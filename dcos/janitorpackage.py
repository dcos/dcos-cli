import json
from urllib.parse import urljoin

import requests
from dcos import (http)


class Janitor():
    """Implementation of janitor"""

    def __init__(self, package_manager, emitter):
        self.package_manager = package_manager
        self.emitter = emitter

    def destroy_volumes(self, master_url, role, principal):
        state = self.get_state_json(master_url)
        if not state or not 'slaves' in state.keys():
            return False
        all_success = True
        for slave in state['slaves']:
            if not self.destroy_volume(slave, master_url, role, principal):
                all_success = False
        return all_success

    def destroy_volume(self, slave, master_url, role, principal):
        volumes = []
        slaveId = slave['id']

        reserved_resources_full = slave.get('reserved_resources_full', None)
        if not reserved_resources_full:
            self.emitter.publish('No reserved resources for any role on slave {}'.format(slaveId))
            return True

        reserved_resources = reserved_resources_full.get(role, None)
        if not reserved_resources:
            self.emitter.publish('No reserved resources for role \'{}\' on slave {}. Known roles are: [{}]'.format(
                role, slaveId, ', '.join(reserved_resources_full.keys())))
            return True

        for reserved_resource in reserved_resources:
            name = reserved_resource.get('name', None)
            disk = reserved_resource.get('disk', None)

            if name == 'disk' and disk != None and 'persistence' in disk:
                volumes.append(reserved_resource)

        self.emitter.publish('Found {} volume(s) for role \'{}\' on slave {}, deleting...'.format(
            len(volumes), role, slaveId))

        req_url = urljoin(master_url, 'destroy-volumes')
        data = {
            'slaveId': slaveId,
            'volumes': json.dumps(volumes)
        }

        response = http.post(req_url, data=data)

        self.emitter.publish('{} {}'.format(response.status_code, response.content))
        success = 200 <= response.status_code < 300
        if response.status_code == 409:
            self.emitter.publish('''###\nIs a framework using these resources still installed?\n###''')
        return success

    def get_state_json(self, master_url):
        __master_versions = {}
        version_num = __master_versions.get(master_url, None)
        slaves_json = None
        if not version_num:
            # get version num from /slaves (and reuse response for volume info if version is >= 28)
            slaves_json = self.get_url(urljoin(master_url, 'slaves'))
            version_num = __master_versions[master_url] = self.extract_version_num(slaves_json)
        if not version_num or version_num >= 28:
            # 28 and after only have the reservation data in /slaves
            if not slaves_json:
                slaves_json = self.get_url(urljoin(master_url, 'slaves'))
            return slaves_json

    def get_url(self, url):
        try:
            response = http.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            self.emitter.publish('HTTP GET request timed out.')
        except requests.exceptions.ConnectionError as err:
            self.emitter.publish('Network error:', err)
        except requests.exceptions.HTTPError as err:
            self.emitter.publish('Invalid HTTP response:', err)
        return None

    def extract_version_num(self, slaves_json):
        '''"0.28.0" => 28'''
        if not slaves_json:
            self.emitter.publish('Bad slaves response')
            return None
        # check the version advertised by the slaves
        for slave in slaves_json.get('slaves', []):
            version = slave.get('version', None)
            if version:
                break
        if not version:
            self.emitter.publish('No version found in slaves list')
        version_parts = version.split('.')
        if len(version_parts) < 2:
            self.emitter.publish('Bad version string: {}'.format(version))
            return None
        num_str = version_parts[1]
        self.emitter.publish('Mesos version: {} => {}'.format(version, num_str))
        return int(num_str)

    def unreserve_resources(self, master_url, role, principal):
        state = self.get_state_json(master_url)
        if not state or not 'slaves' in state.keys():
            return False
        all_success = True
        for slave in state['slaves']:
            if not self.unreserve_resource(slave, master_url, role, principal):
                all_success = False
        return all_success

    def unreserve_resource(self, slave, master_url, role, principal):
        resources = []
        slaveId = slave['id']

        reserved_resources_full = slave.get('reserved_resources_full', None)
        if not reserved_resources_full:
            self.emitter.publish('No reserved resources for any role on slave {}'.format(slaveId))
            return True

        reserved_resources = reserved_resources_full.get(role, None)
        if not reserved_resources:
            self.emitter.publish('No reserved resources for role \'{}\' on slave {}. Known roles are: [{}]'.format(
                role, slaveId, ', '.join(reserved_resources_full.keys())))
            return True

        for reserved_resource in reserved_resources:
            resources.append(reserved_resource)

        self.emitter.publish('Found {} resource(s) for role \'{}\' on slave {}, deleting...'.format(
            len(resources), role, slaveId))

        req_url = urljoin(master_url, 'unreserve')
        data = {
            'slaveId': slaveId,
            'resources': json.dumps(resources)
        }

        response = http.post(req_url, data=data)

        self.emitter.publish('{} {}'.format(response.status_code, response.content))
        return 200 <= response.status_code < 300

    def delete_zk_node(self, exhibitor_url, znode):
        """Delete Zookeeper node via Exhibitor (eg http://leader.mesos:8181/exhibitor/v1/...)"""
        znode_url = urljoin(exhibitor_url, '/exhibitor/v1/explorer/znode/{}'.format(znode))

        try:
            response = http.delete(znode_url, timeout=5, verify=False)
        except requests.exceptions.Timeout:
            self.emitter.publish('HTTP DELETE request timed out.')
            return False
        except requests.exceptions.ConnectionError as err:
            self.emitter.publish('Network error:', err)
            return False
        except requests.exceptions.HTTPError as err:
            self.emitter.publish('Invalid HTTP response:', err)
            return False

        if 200 <= response.status_code < 300:
            self.emitter.publish('Successfully deleted znode \'{}\' (code={}), if znode existed.'.format(
                znode, response.status_code))
            return True
        else:
            self.emitter.publish('ERROR: HTTP DELETE request returned code:', response.status_code)
            self.emitter.publish('Response body:', response.text)
            return False