from conans import ConanFile, CMake, AutoToolsBuildEnvironment, tools
import os, glob, shutil


class CyrusSaslConan(ConanFile):
    name = "openssl-gost-engine"
    version = "3.0.1+2"
    license = "Apache License v2.0"
    description = "OpenLDAP C++ library"
    url = "https://github.com/gost-engine/engine"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "dll_sign": [True, False],
        "ninja": [False, True],
        "shared": [True, False]
    }
    exports_patches = [
          "patches/0001-CMakeLists.txt.patch"
        , "patches/0002-add_conan.cmake.patch"
        , "patches/0003-add_gost_engine.rc.patch"
        , "patches/0004-gost_grasshopper_math.h.patch"
        , "patches/0005-gost12sum.c.patch"
        , "patches/0006-CMakeLists.txt.disable_warn_as_error.patch"
    ]
    default_options = "dll_sign=True", "ninja=True", "shared=True"
    generators = "cmake"
    exports_sources = "src/*", *exports_patches
    no_copy_source = True
    build_policy = "missing"
    #
    _openssl_version = "3.0.7+2"
    _openssl_channel = "stable"

    def configure(self):
        if self.settings.compiler.get_safe("libcxx") == "libstdc++":
            raise Exception("This package is only compatible with libstdc++11")
        # MT(d) static library
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            if self.settings.compiler.runtime == "MT" or self.settings.compiler.runtime == "MTd":
                self.options.shared=False
        # DLL sign, only Windows and shared
        if self.settings.os != "Windows" or self.options.shared == False:
            del self.options.dll_sign

    def build_requirements(self):
        if self.options.get_safe("ninja"):
            self.build_requires("ninja/[>=1.10.2]")
        if self.options.get_safe("dll_sign"):
            self.build_requires("windows_signtool/[>=1.1]@%s/stable" % self.user)

    def requirements(self):
        self.requires("openssl/%s@%s/%s" % (self._openssl_version, self.user, self._openssl_channel))

    def source(self):
        for patch in self.exports_patches:
            tools.patch(patch_file=patch)

    def build(self):
        build_type = "RelWithDebInfo" if self.settings.build_type == "Release" else "Debug"
        generator = "Ninja" if self.options.ninja == True else None
        cmake = CMake(self, build_type=build_type, generator=generator)
        cmake.verbose = False
        source_folder = "./src"
        cmake.configure(source_folder=source_folder)
        cmake.build()
        cmake.install()

    def package_id(self):
        self.info.options.ninja = "any"

    def package(self):
        # Sign DLL
        if self.options.get_safe("dll_sign"):
            import windows_signtool
            pattern = os.path.join(self.package_folder, "bin", "*.dll")
            for fpath in glob.glob(pattern):
                fpath = fpath.replace("\\", "/")
                for alg in ["sha1", "sha256"]:
                    is_timestamp = True if self.settings.build_type == "Release" else False
                    cmd = windows_signtool.get_sign_command(fpath, digest_algorithm=alg, timestamp=is_timestamp)
                    self.output.info("Sign %s" % fpath)
                    self.run(cmd)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)

    def imports(self):
        self.copy("*.dll", "bin", "bin")
