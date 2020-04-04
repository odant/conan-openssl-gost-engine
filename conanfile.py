from conans import ConanFile, CMake, AutoToolsBuildEnvironment, tools
import os, glob, shutil


class CyrusSaslConan(ConanFile):
    name = "openssl-gost-engine"
    version = "1.1.0.4-beta4"
    license = "Apache License v2.0"
    description = "OpenLDAP C++ library"
    url = "https://github.com/gost-engine/engine"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "dll_sign": [True, False],
        "ninja": [False, True],
        "shared": [True, False]
    }
    default_options = "dll_sign=True", "ninja=True", "shared=True"
    generators = "cmake"
    exports_sources = "src/*", "openssl-gost-engine.patch"
    no_copy_source = True
    build_policy = "missing"
    #
    _openssl_version = "1.1.1f+0"
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
            self.build_requires("ninja_installer/1.9.0@bincrafters/stable")
        if self.options.get_safe("dll_sign"):
            self.build_requires("windows_signtool/[>=1.1]@%s/stable" % self.user)

    def requirements(self):
        self.requires("openssl/%s@%s/%s" % (self._openssl_version, self.user, self._openssl_channel))

    def source(self):
        tools.patch(patch_file="openssl-gost-engine.patch")

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
