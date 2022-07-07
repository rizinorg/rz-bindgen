{ pkgs ? import <nixpkgs> {} }:

let
  clang-cflags = pkgs.lib.concatStringsSep " "
    (builtins.concatMap
      (f: pkgs.lib.splitString "\n"
        (builtins.readFile "${pkgs.clang}/nix-support/${f}"))
      ["cc-cflags" "libc-cflags"]);
in
pkgs.mkShell {
  buildInputs = with pkgs; [ python3 mypy black pylint swig4 meson ninja ];

  RIZIN_INC_PATH = "${pkgs.rizin}/include/librz";
  CLANG_PATH = "${pkgs.libclang.lib}/lib";
  CLANG_ARGS = "${clang-cflags} -I${pkgs.openssl.dev}/include";
  
  # Nix usage:
  # python3 main.py --clang-path $CLANG_PATH --rizin-inc-path $RIZIN_INC_PATH $CLANG_ARGS
}
