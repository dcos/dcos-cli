#!/bin/bash

while true; do
  sudo stop mesos-slave
  sleep 30
  sudo start mesos-slave
  sleep 10
done
