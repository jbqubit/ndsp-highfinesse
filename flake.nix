# This is a stand-alone valon nix environment suitable for development of the driver.
# A different script will show how to intergrate the valon with an existing artiq environment. 

{
    description = "NDSP for HighFinesse wavemeter in Britton Lab";

    inputs.nixpkgs.url = "github:nixos/nixpkgs?rev=22612485a469d71df09b9434842767b1f4f2c063";
    
    outputs = { self, nixpkgs }:
        let 
        pkgs = nixpkgs.legacyPackages.x86_64-linux; 
        sipyco = pkgs.python3Packages.buildPythonPackage rec {
            pname = "sipyco";
            version = "1.2";
            src = pkgs.fetchFromGitHub {
                owner = "m-labs";
                repo = "sipyco";
                rev = "v${version}";
                sha256 = "02x2s66x9bbzj82d823vjg2i73w7iqwvkrjbbyrsav6ccj7f90sj";
            };
            propagatedBuildInputs = with pkgs.python3Packages; [ numpy ];
        };
    in {
        defaultPackage.x86_64-linux = pkgs.python3Packages.buildPythonApplication ({
                name = "aqctl_highfinesse";
                version = "1.0";
                src = ./.;
                propagatedBuildInputs = [ sipyco ];
        });
    };
}

