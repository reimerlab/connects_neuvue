#!/bin/bash

# Check if the script is called with a tag for docker image
TAG=${1:-latest} # Use "latest" as default if no argument is provided
PUSH=${2:-0} # Use "0" as default if no second argument is provided

# Check if the connects_neuvue folder exists
if [ -d "connects_neuvue" ]; then
    echo "Directory 'connects_neuvue' exists. Pulling latest changes..."
    cd connects_neuvue && git pull && cd ..
else
    echo "Directory 'connects_neuvue' does not exist. Cloning repository..."
    git clone https://github.com/reimerlab/connects_neuvue
fi

# Build the Docker image
docker buildx build --no-cache -t jr-saltmaster.ad.bcm.edu:5000/h01_neuvue:$TAG --load -f Dockerfile .

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Docker build successful."
    # Check if the second argument is "1" to push the image
    if [ "$PUSH" -eq 1 ]; then
        echo "Pushing the Docker image..."
        docker push jr-saltmaster.ad.bcm.edu:5000/h01_neuvue:$TAG
    fi
else
    echo "Docker build failed. Exiting."
    exit 1
fi