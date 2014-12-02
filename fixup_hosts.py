
import json
import subprocess

output = json.loads(subprocess.check_output(
    ['gcloud', 'compute', 'instances', 'list', '--format=json']))

demo_hosts = []
for i in output:
    if not "demo" in i["name"]:
        continue

    try:
        ip = i["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
    except:
        continue
    host = "{}.c.inbound-bee-664.internal".format(i["name"])
    demo_hosts.append("{}\t{}".format(ip, host))

host_file = [l for l in open("/etc/hosts", "r+").read().split("\n")
    if not "664.internal" in l] + demo_hosts

open("/etc/hosts", "w").write("\n".join(host_file))
