ITER=0

while [ true ]; do
  echo "Iteration: ${ITER}"
  rm -rf sleep
  dcos task exec --interactive gpu-test cat /bin/sleep > sleep
  RET="${?}"
  if [ "${RET}" != "0" ]; then
    echo "Error: ${RET}"
    exit 1
  fi
  chmod a+x sleep
  ./sleep 0.5
  ITER=$(expr ${ITER} + 1)
done
