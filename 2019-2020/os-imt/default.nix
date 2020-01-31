with import <nixpkgs> {};

let packageOverrides = self: super: {
    # Override python-language-server at top level to make it effective 
    # also for for isort and mypy
    python-language-server = super.python-language-server.override {
      # Only make few features available
      # https://github.com/NixOS/nixpkgs/blob/e5a015bd85f6d1578702aaa7e710b028775c76aa/pkgs/development/python-modules/python-language-server/default.nix
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
  buildInputs = [ py-dev pipenv libffi openssl ];
  shellHook = ''
    # Set SOURCE_DATE_EPOCH so that we can use python wheels
    SOURCE_DATE_EPOCH=$(date +%s)

    # Set PYTHONPATH to empty to fix `pipenv install`
    PYTHONPATH=
  '';
}
