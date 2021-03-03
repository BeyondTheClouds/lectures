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
  py-dev = (python38.override {inherit packageOverrides;}).withPackages (py-pkg: [
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

    # Mount /bin in the tmpfs so that I can symlink bash into /bin
    # without messing my nix config
    #
    # http://blog.programster.org/overlayfs/
    # https://news.ycombinator.com/item?id=5024654
    # E.g, protect your home:
    # > mount -t overlay -o lowerdir=~/,upperdir=/tmp/tmpHOME\
    # > my-overlay ~/
    # - lowerdir: Files in lowerdir appear in the overlay
    # - upperdir: where creation/modification are stored
    # - workdir: Needs to be an empty directory on the same fs as
    #   upperdir (merge of lower/upper)
    # - my-overlay: Name of the overlay for latter umount (e.g. `sudo
    #   umount my-overlay`)
    # - Any file created or changed in overlay appear
    #   in the upper dir
    OVERLAY_NAME="bin-bash-overlay$(pwd | sed -e 's|/|-|g')"
    function teardown() {
      echo "INFO: umount $OVERLAY_NAME."
      sudo umount "$OVERLAY_NAME"
    }

    if ! fgrep -q '$OVERLAY_NAME on /bin' <<< $(mount -l)
    then
      echo "INFO: Kolla/tools uses #!/bin/bash not linked in NixOS"
      echo "INFO: Make an overlayfs on /bin and link bash in /bin"
      echo "INFO: mount $OVERLAY_NAME."

      UPP_BIN="$(mktemp -d)"
      WORK_BIN="$(mktemp -d)"

      sudo mount --types overlay --options \
        lowerdir=/bin,upperdir=$UPP_BIN,workdir=$WORK_BIN \
        "$OVERLAY_NAME" /bin

      ln --symbolic --verbose /run/current-system/sw/bin/bash /bin/bash
    fi

    # teardown on CTRL+d
    trap "teardown" exit
  '';
}
