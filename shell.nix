{ pkgs ? import <nixpkgs> {} }:

let
  # Common environment variables
  envVars = {
    NODE_ENV = "development";
  };

in pkgs.mkShell {
  buildInputs = with pkgs; [
    docker
    docker-compose
    nodejs_18
    nodemon
    nodePackages.ts-node
  ];

  shellHook = ''
    echo "Sync packages"
    uv sync

    # Activate venv
    if [ -d ".venv" ]; then
      source .venv/bin/activate
    else
      echo "Virtual environment not found, creating one..."
    fi
    alias python='python3'
    alias dev1='python3 main.py'
    alias dev='nodemon'

    which python3

  '';
}