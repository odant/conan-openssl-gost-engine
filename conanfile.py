from conan import ConanFile, tools
import os, glob, shutil


class OpenSSLGOSTEngine(ConanFile):
    name = "openssl-gost-engine"
    version = "3.0.3+1"
    license = "Apache License v2.0"
    description = "A reference implementation of the Russian GOST crypto algorithms for OpenSSL"
    url = "https://github.com/gost-engine/engine"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "dll_sign": [True, False],
        "ninja": [False, True],
        "shared": [True, False]
    }
    exports_patches = [
          "patches/0001-CMakeLists.txt.patch"
        , "patches/0003-add_gost_engine.rc.patch"
        , "patches/0004-gost_grasshopper_math.h.patch"
        , "patches/0005-gost12sum.c.patch"
        , "patches/0006-CMakeLists.txt.disable_warn_as_error.patch"
        , "patches/0007-getopt.h.fixup_clangcl_build.patch"
    ]
    default_options = { 
        "dll_sign": True,
        "ninja":    True, 
        "shared":   True
    }
    exports_sources = "src/*", *exports_patches
    no_copy_source = True
    build_policy = "missing"
    package_type = "library"
    python_requires = "windows_signtool/[>=1.2]@odant/stable"
    
    def layout(self):
        tools.cmake.cmake_layout(self, src_folder="src")

    def configure(self):
        if self.settings.compiler.get_safe("libcxx") == "libstdc++":
            raise Exception("This package is only compatible with libstdc++11")
        # MT(d) static library
        if self.settings.os == "Windows" and self.settings.compiler == "msvc":
            if self.settings.compiler.runtime == "static":
                self.options.shared=False
        # DLL sign, only Windows and shared
        if self.settings.os != "Windows" or self.options.shared == False:
            self.options.rm_safe("dll_sign")

    def build_requirements(self):
        if self.options.get_safe("ninja"):
            self.build_requires("ninja/[>=1.12.1]")

    def requirements(self):
        self.requires("openssl/[>=3.0.16]@%s/stable" % self.user)

    def source(self):
        for patch in self.exports_patches:
            tools.files.patch(self, patch_file=patch)
    
    def generate(self):
        benv = tools.env.VirtualBuildEnv(self)
        benv.generate()
        renv = tools.env.VirtualRunEnv(self)
        renv.generate()
        if tools.microsoft.is_msvc(self):
            vc = tools.microsoft.VCVars(self)
            vc.generate()
        deps = tools.cmake.CMakeDeps(self)    
        deps.generate()
        cmakeGenerator = "Ninja" if self.options.ninja else None
        tc = tools.cmake.CMakeToolchain(self, generator=cmakeGenerator)
        tc.generate()

    def build(self):
        cmake = tools.cmake.CMake(self)
        cmake.configure()
        cmake.build()

    def package_id(self):
        self.info.options.ninja = "any"

    def package(self):
        cmake = tools.cmake.CMake(self)
        cmake.install()
        # Sign DLL
        if self.options.get_safe("dll_sign"):
            self.python_requires["windows_signtool"].module.sign(self, [os.path.join(self.package_folder, "bin", "*.dll")])

    def package_info(self):
        self.cpp_info.libs = tools.files.collect_libs(self)
