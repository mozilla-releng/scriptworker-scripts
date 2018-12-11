let
  pkgsJSON = builtins.fromJSON (builtins.readFile ./nixpkgs.json);
  pypi2nixJSON = builtins.fromJSON (builtins.readFile ./pypi2nix.json); 
  pkgsSrc = builtins.fetchTarball { inherit (pkgsJSON) url sha256; };
  pypi2nixSrc = builtins.fetchTarball { inherit (pypi2nixJSON) url sha256; };
  overlay = self: super: {
    pypi2nix = import pypi2nixSrc { pkgs = self; };
  };
in
{ pkgs ? import pkgsSrc { config = {}; overlays = [ overlay ]; }
}:

let
  python = import ./requirements.nix { inherit pkgs; };
  version = builtins.replaceStrings ["\n"] [""]
    (builtins.readFile (toString ../version.txt));

  self = python.mkDerivation rec {
    name = "shipitscript-${version}";
    src = builtins.filterSource pkgs.lib.cleanSourceFilter ../.;
    doCheck = false;
    buildInputs = builtins.attrValues python.packages;
    propagatedBuildInputs = with python.packages; [
      scriptworker
      shipitapi
    ];

    passthru = {
      inherit python;

      docker = pkgs.dockerTools.buildLayeredImage {
        name = "shipitscript";
        tag = version;
        contents = [
          self
        ];
      };

      # to update the dependencies run the following 2 commands:
      # nix-build -A update
      # ./result
      update = pkgs.writeScript "update-${self.name}" ''
        pushd ${toString ./.}
        ${pkgs.pypi2nix}/bin/pypi2nix \
          -V 3.7 \
          -r ../requirements.txt \
          -e flit \
          -e intreehooks \
          -e vcversioner \
          -e pytest-runner \
          -e setuptools-scm
      '';

      tarball =
        let
          closureInfo = pkgs.closureInfo { rootPaths = [ self ]; };
        in
          pkgs.runCommand "${self.name}.nix.tar.gz" {} ''
            mkdir -p nix/store bin
            # TODO: add some metadata?
            for d in $(cat ${closureInfo}/store-paths); do
              cp -a $d nix/store
            done
            ln -s ${self}/bin/shipitscript bin/
            tar -czf $out --exclude=.attr-0 --exclude=env-vars .
          '';

    };

  };

in self
