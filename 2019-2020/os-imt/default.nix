# Painlessly developing Python on NixOS
# https://sid-kap.github.io/posts/2018-03-08-nix-pipenv.html

with import <nixpkgs> {};
with import <nixpkgs/nixos> {};

# let py = python37.withPackages (pkgs: with pkgs; [
#   # These are for spacemacs python layer. To get spacemacs with the
#   # correct PATH. run nix-shell, then launch Emacs inside this
#   # nix-shell.
#   ]);
let manylinux1Bin = [
    which gcc binutils stdenv
  ];
  manylinux1File = writeTextDir "_manylinux.py" ''
    print("in _manylinux.py")
    manylinux1_compatible = True
  '';
  packageOverrides = self: super: {
    # Override python-language-server, including for isort and mypy
    # https://github.com/NixOS/nixpkgs/blob/e5a015bd85f6d1578702aaa7e710b028775c76aa/pkgs/development/python-modules/python-language-server/default.nix
    python-language-server = super.python-language-server.override {
      # Only enable few features
      providers = [
        "pycodestyle"  # Style linting (Ex-pep8)
        "pyflakes"     # Error linting (no style)
      ];
    };
  };
  py-dev = (python37.override {inherit packageOverrides;}).withPackages (py-pkg: [
                py-pkg.python-language-server
                py-pkg.pyls-isort
                py-pkg.pyls-mypy
            ]);
in mkShell {
  buildInputs = [ py-dev pipenv manylinux1Bin libffi openssl ];
  # profile = ''
  #   export PYTHONPATH=${manylinux1File.out}:/usr/lib/python3.7/site-packages
  # '';
  # runScript = "$SHELL";
  # shellHook = ''
  #   export PYTHONPATH=${manylinux1File.out}:''${PYTHONPATH}

  #   # spacemacs deps
  #   # pipenv install --dev python-language-server[yapf]
  #   # pipenv install --dev pyls-isort
  #   # pipenv install --dev pyls-mypy
  #   # pipenv run pip install ipdb

  #   # # dev deps
  #   # pip install tox
  #   # pip install -r requirements.txt
  #   # pip install -r test-requirements.txt
  # '';
}
