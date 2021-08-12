# QontainerNet

QontainerNet is a ComNetsEmu extension that enables the simulation of quantum enhanced communication links. Currently the project contains three types of quantum enhanced links.

1. Fully Quantum Mechanically Simulated GEWI Link
    Full quantum simulation is ran inside of docker container with QuNetSim.
2. Simplified GEWI [1] Link
    Based on quantum mechanical parameters the traffic is delayed.
3. Interface based GEWI [1] link
    The behaviour of GEWI protocol is modeled with Token Bucket Filter.

## Installation
This project should be ran inside of a ComNetsEmu virtual machine.
In order to install ComNetsEmu, please refer to [ComNetsEmu README](https://git.comnets.net/public-repo/comnetsemu).

After logging into the ComNetsEmu VM make sure that `git` and `docker-compose` are installed.

To clone the project, run:
`
git clone git@github.com:tqsd/QontainerNet.git
`

Prior to running an example, Docker containers need to be built. To run QontainerNet you need to build at least two containers. To build them run the `setup.sh` script.

## Usage
Run an example with :
 `
 sudo python3 example.py
 `


[1] Nötzel, Janis, and Stephen DiAdamo. "Entanglement-assisted data transmission as an enabling technology: A link-layer perspective." 2020 IEEE International Symposium on Information Theory (ISIT). IEEE, 2020.
