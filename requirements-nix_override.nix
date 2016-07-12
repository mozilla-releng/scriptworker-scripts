{ pkgs, python }:

self: super: {
  "pefile" = python.mkDerivation {
    name = "pefile-2016.3.28";
    src = pkgs.fetchFromGitHub {
      owner = "erocarrera";
      repo = "pefile";
      sha256 = "18j9s3bmmq81gvgfa4bbrf8b2ybak09isw48hz5fc29538nwc2sx";
      rev = "ac410dcf7fff6840a06bc50e374f4b4db33e0c0e";
    };
    doCheck = false;
    buildInputs = [];
    propagatedBuildInputs = [
      self."future"
    ];
    passthru.top_level = false;
  };

  "jsonschema" = python.overrideDerivation super."jsonschema" (old: {
    buildInputs = old.buildInputs ++ [ self."vcversioner" ];
  });

  "mccabe" = python.overrideDerivation super."mccabe" (old: {
    buildInputs = old.buildInputs ++ [ self."pytest-runner" ];
  });

  "signtool" = python.overrideDerivation super."signtool" (old: {
    propagatedBuildInputs = old.propagatedBuildInputs ++ [ self."pefile" ];
  });

  "pytest-runner" = python.overrideDerivation super."pytest-runner" (old: {
    buildInputs = old.buildInputs ++ [ self."setuptools-scm" ];
  });

}
