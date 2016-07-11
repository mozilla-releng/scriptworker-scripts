{ }:
let
  pkgs = import <nixpkgs> {};
  signingscript = import ./default.nix { inherit pkgs; };
in {
  docker = pkgs.dockerTools.buildImage {
    name = "docker-${signingscript.name}";
    tag = (builtins.parseDrvName signingscript.name).version;
    fromImage = null;
    contents = [ pkgs.busybox signingscript ];
    config = {
      Cmd = [ "python" "-m" "signingscript" ];
    };
  };
}
