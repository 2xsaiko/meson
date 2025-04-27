---
title: Swift
short-description: Compiling Swift sources
---

# Compiling Swift applications

Meson has support for compiling Swift programs. A minimal *meson.build* file for Swift looks like this:

```meson
project('myapp', 'swift')

executable('myapp', 'main.swift')
```

The Swift language version can be set using the *swift_std* option.

```meson
project('myapp', 'swift', default_options: {'swift_std': '6'})

executable('myapp', 'main.swift')
```

# Library linking

Meson supports creating both static and shared Swift libraries. To link a Swift target to another, add it to the link_with kwarg of the target it should be linked into. The library will then be available for use in the other target.

# Handling of top-level code

In library targets, source files named 'main.swift' execute top-level statements at program start. In executable targets, this additionally happens when the target only has one Swift source file. If this is a problem, such as when duplicate main symbols occur when linking, avoid naming the source file 'main.swift', or add *-parse-as-library* to swift_args.

# Using C/C++/Obj-C code from Swift

to do

# Using Swift code from C/C++/Obj-C

to do

# Using Swift and C/C++/Obj-C code in the same target

to do

# Caveats

## Installing libraries and finding dependencies

Installing Swift module interface and writing pkg-config files for it is currently not implemented.

## SwiftPM integration

Meson does not support importing SwiftPM packages (Package.swift) directly. To use these packages, wrap files must be hand-written.

## Package-level visibility

Meson does not automatically set up package-level visibility for targets. To use this in Swift code, add the *-package-name* flag to swift_args with a unique name.

```meson
project('myapp', 'swift')

myapp_package = ['-package-name', 'myapp']

lib = library('applib', 'Library.swift', swift_args: [myapp_package])
executable('myapp', 'main.swift', dependencies: [lib], swift_args: [myapp_package])
```

## Toolchain compatibility

The Swift toolchain ships its own Clang compiler. On systems other than macOS, this is usually not the default C compiler. If interoperability with C++ is a concern, it is advised to use the Clang compiler in the Swift toolchain to compile C/C++ code, especially when using Swift code from C++.

On non-macOS systems that use LLVM libc++ as the C++ STL, be aware that the libc++ version has to be compatible with the Clang version shipped in the Swift compiler, which is often several major versions behind. Libc++ currently supports the same major version of Clang and additionally the previous two major versions, for example Clang 18, 19, 20 for libc++ 20. You may have to hold back major version updates for libc++ on such a system to stay compatible with Swift.

## ABI stability

While Meson allows building and installing Swift libraries on any platform, be aware that Swift only has a stable ABI
on Apple platforms.

## Bundles

Meson does not currently support automatically producing bundles for use with the Foundation.Bundle class.
