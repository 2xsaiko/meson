# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2017 The Meson development team

from __future__ import annotations

import re
import subprocess, os.path
import typing as T

from .. import mlog, options
from ..mesonlib import EnvironmentException, first, MesonException, version_compare
from .compilers import Compiler, clike_debug_args


if T.TYPE_CHECKING:
    from .. import build
    from ..options import MutableKeyedOptionDictType
    from ..dependencies import Dependency
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..linkers.linkers import DynamicLinker
    from ..mesonlib import MachineChoice

swift_optimization_args: T.Dict[str, T.List[str]] = {
    'plain': [],
    '0': [],
    'g': [],
    '1': ['-O'],
    '2': ['-O'],
    '3': ['-O'],
    's': ['-O'],
}

swiftc_color_args: T.Dict[str, T.List[str]] = {
    'auto': [],
    'always': ['-color-diagnostics'],
    'never': ['-no-color-diagnostics'],
}

class SwiftCompiler(Compiler):

    LINKER_PREFIX = ['-Xlinker']
    language = 'swift'
    id = 'llvm'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo', full_version: T.Optional[str] = None,
                 linker: T.Optional['DynamicLinker'] = None):
        super().__init__([], exelist, version, for_machine, info,
                         is_cross=is_cross, full_version=full_version,
                         linker=linker)
        self.version = version
        if self.info.is_darwin():
            try:
                self.sdk_path = subprocess.check_output(['xcrun', '--show-sdk-path'],
                                                        universal_newlines=True,
                                                        encoding='utf-8', stderr=subprocess.STDOUT).strip()
            except subprocess.CalledProcessError as e:
                mlog.error("Failed to get Xcode SDK path: " + e.output)
                raise MesonException('Xcode license not accepted yet. Run `sudo xcodebuild -license`.')
            except FileNotFoundError:
                mlog.error('xcrun not found. Install Xcode to compile Swift code.')
                raise MesonException('Could not detect Xcode. Please install it to compile Swift code.')

    def get_pic_args(self) -> T.List[str]:
        return []

    def get_pie_args(self) -> T.List[str]:
        return []

    def needs_static_linker(self) -> bool:
        return True

    def get_werror_args(self) -> T.List[str]:
        return ['-warnings-as-errors']

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        return ['-emit-dependencies']

    def get_dependency_compile_args(self, dep: Dependency) -> T.List[str]:
        args = dep.get_compile_args()
        # Some deps might sneak in a hardcoded path to an older macOS SDK, which can
        # cause compilation errors. Let's replace all .sdk paths with the current one.
        # SwiftPM does it this way: https://github.com/swiftlang/swift-package-manager/pull/6772
        # Not tested on anything else than macOS for now.
        if not self.info.is_darwin():
            return args
        pattern = re.compile(r'.*\/MacOSX[^\/]*\.sdk(\/.*|$)')
        for i, arg in enumerate(args):
            if arg.startswith('-I'):
                match = pattern.match(arg)
                if match:
                    args[i] = '-I' + self.sdk_path + match.group(1)
        return args

    def depfile_for_object(self, objfile: str) -> T.Optional[str]:
        return os.path.splitext(objfile)[0] + '.' + self.get_depfile_suffix()

    def get_depfile_suffix(self) -> str:
        return 'd'

    def get_output_args(self, target: str) -> T.List[str]:
        return ['-o', target]

    def get_header_import_args(self, headername: str) -> T.List[str]:
        return ['-import-objc-header', headername]

    def get_colorout_args(self, colortype: str) -> T.List[str]:
        return swiftc_color_args[colortype][:]

    def get_warn_args(self, level: str) -> T.List[str]:
        return []

    def get_std_exe_link_args(self) -> T.List[str]:
        return ['-emit-executable']

    def get_std_shared_lib_link_args(self) -> T.List[str]:
        return ['-emit-library']

    def get_module_args(self, modname: str) -> T.List[str]:
        return ['-module-name', modname]

    def get_mod_gen_args(self) -> T.List[str]:
        return ['-emit-module']

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        return ['-I' + path]

    def get_compile_only_args(self) -> T.List[str]:
        return ['-c']

    def get_options(self) -> MutableKeyedOptionDictType:
        opts = super().get_options()

        key = self.form_compileropt_key('std')
        opts[key] = options.UserComboOption(
            self.make_option_name(key),
            'Swift language version.',
            'none',
            # List them with swiftc -frontend -swift-version ''
            choices=['none', '4', '4.2', '5', '6'])

        return opts

    def get_option_std_args(self, target: build.BuildTarget, env: Environment, subproject: T.Optional[str] = None) -> T.List[str]:
        args: T.List[str] = []

        std = self.get_compileropt_value('std', env, target, subproject)
        assert isinstance(std, str)

        if std != 'none':
            args += ['-swift-version', std]

        # Pass C compiler args to swiftc, notably -std=...
        c_langs = ['objc', 'c']
        if self.supports_cxx_interoperability():
            c_langs = ['objcpp', 'cpp', *c_langs]

        c_lang = first(c_langs, lambda x: x in target.compilers)
        if c_lang is not None:
            cc = target.compilers[c_lang]
            args.extend(arg for c_arg in cc.get_option_compile_args(target, env, subproject) for arg in ['-Xcc', c_arg])

        return args

    def get_working_directory_args(self, path: str) -> T.Optional[T.List[str]]:
        if version_compare(self.version, '<4.2'):
            return None

        return ['-working-directory', path]

    def get_cxx_interoperability_args(self, enabled: bool) -> T.List[str]:
        if not self.supports_cxx_interoperability():
            if enabled:
                raise MesonException(f'Compiler {self} does not support C++ interoperability')
            return []
        if enabled:
            return ['-cxx-interoperability-mode=default']
        else:
            return ['-cxx-interoperability-mode=off']

    def supports_cxx_interoperability(self) -> bool:
        return version_compare(self.version, '>=5.9')

    def get_pch_output_dir_args(self, output_dir: str) -> T.List[str]:
        return ['-pch-output-dir', output_dir]

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        src = 'swifttest.swift'
        source_name = os.path.join(work_dir, src)
        output_name = os.path.join(work_dir, 'swifttest')
        extra_flags: T.List[str] = []
        extra_flags += environment.coredata.get_external_args(self.for_machine, self.language)
        if self.is_cross:
            extra_flags += self.get_compile_only_args()
        else:
            extra_flags += environment.coredata.get_external_link_args(self.for_machine, self.language)
        with open(source_name, 'w', encoding='utf-8') as ofile:
            ofile.write('''print("Swift compilation is working.")
''')
        pc = subprocess.Popen(self.exelist + extra_flags + ['-emit-executable', '-o', output_name, src], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('Swift compiler %s cannot compile programs.' % self.name_string())
        if self.is_cross:
            # Can't check if the binaries run so we have to assume they do
            return
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by Swift compiler %s are not runnable.' % self.name_string())

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        return clike_debug_args[is_debug]

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return swift_optimization_args[optimization_level]
