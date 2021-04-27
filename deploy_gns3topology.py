import getpass
import yaml
import json
import requests
import time
import subprocess
from netmiko import ConnectHandler
import logging

def new_project(name):
    ### Finding the project ID if a project with the given name exists.
    url = "http://%s:%s/v2/projects" % (CONFIG["gns3_server"], CONFIG["gns3_port"])
    response = requests.get(url, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
    if response.status_code == 200:
        body = response.json()
        project = next((item for item in body if item["name"] == CONFIG["project_name"]), None)
    else:
        print("Received HTTP error %d when checking if the project already exists! Exiting." % response.status_code)
        exit(1)

    ### Deleting the project if it already exists.
    if project != None:
        while True:
            #query = input('The project does already exist. Would you like to delete the existing project? (y/n):')
            query = 'y'
            answer = query[0].lower()
            if query == '' or not answer in ['y','n']:
                print('Please answer with yes or no')
            else:
                break
        if answer == 'y':
            print('INFO: Deleting the existing project.')
            url = "http://%s:%s/v2/projects/%s" % (CONFIG["gns3_server"], CONFIG["gns3_port"], project["project_id"])
            response = requests.delete(url, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
            if response.status_code != 204:
                print("Received HTTP error %d when deleting the existing project! Exiting." % response.status_code)
                exit(1)
        elif answer == 'n':
            print('INFO: Stopping script.')
            exit(1)

    ### (Re)creating the project
    url = "http://%s:%s/v2/projects" % (CONFIG["gns3_server"], CONFIG["gns3_port"])
    data = {"name": CONFIG["project_name"]}
    data_json = json.dumps(data)
    response = requests.post(url, data=data_json, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
    if response.status_code == 201:
        body = response.json()
        # Adding the project ID to the config
        CONFIG["project_id"] = body["project_id"]
        print('INFO: The new project has been created.')
    else:
        print("Received HTTP error %d when creating the project! Exiting." % response.status_code)
        exit(1)

def assign_template_id():
    node_seq = 0
    url = "http://%s:%s/v2/templates" % (CONFIG["gns3_server"], CONFIG["gns3_port"])
    response = requests.get(url, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
    if response.status_code == 200:
        body = response.json()
        for node in CONFIG["nodes"]:
            node_dict = next((item for item in body if item["name"] == node["template_name"]), None)
            node_template_id = node_dict["template_id"]
            CONFIG["nodes"][node_seq]["template_id"] = node_template_id
            node_seq += 1
    else:
        print("Received HTTP error %d when retrieving templates! Exiting." % response.status_code)
        exit(1)

def add_nodes():
    for instance in CONFIG["nodes"]:
        url = "http://%s:%s/v2/projects/%s/templates/%s" % (CONFIG["gns3_server"], CONFIG["gns3_port"], CONFIG["project_id"], instance["template_id"])
        data = {"compute_id": "vm", "name": instance["name"], "x": instance["x_position"], "y": instance["y_position"]}
        data_json = json.dumps(data)
        response = requests.post(url, data=data_json, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
        body = response.json()
        instance["node_id"] = body["node_id"]
        instance["console_host"] = body["console_host"]
        instance["console"] = body["console"]
        if response.status_code == 201:
            print("The node %s has been created." % (instance["name"]))
        else:
            print("Received HTTP error %d when adding node %s! Exiting." % (response.status_code, instance["name"]))
            exit(1)

def set_nodes():
    for instance in CONFIG["nodes"]:
        url = "http://%s:%s/v2/projects/%s/nodes/%s" % (CONFIG["gns3_server"], CONFIG["gns3_port"], CONFIG["project_id"], instance["node_id"])
        data = {"name": instance["name"]}
        data_json = json.dumps(data)
        response = requests.put(url, data=data_json, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
        body = response.json()
        if response.status_code == 200:
            print("The nodename %s has been set for instance %s." % (instance["name"], instance["node_id"]))
        else:
            print("Received HTTP error %d when setting the nodename for node %s! Exiting." % (response.status_code, instance["name"]))
            exit(1)

def add_links():
    for link in CONFIG["links"]:
        nodecounter = 0
        nodedata = list()
        for node in link["link"]:
            nodedata.append(next((item for item in CONFIG["nodes"] if item["name"] == link["link"][nodecounter]["name"]), None))
            url = "http://%s:%s/v2/projects/%s/nodes/%s" % (CONFIG["gns3_server"], CONFIG["gns3_port"], CONFIG["project_id"], nodedata[nodecounter]["node_id"])
            response = requests.get(url, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
            body = response.json()
            nodedata[nodecounter]["adapter_number"] = body["ports"][link["link"][nodecounter]["interface"]]["adapter_number"]
            nodedata[nodecounter]["port_number"] = body["ports"][link["link"][nodecounter]["interface"]]["port_number"]
            nodecounter = nodecounter + 1
        if nodecounter == 2:
            url = "http://%s:%s/v2/projects/%s/links" % (CONFIG["gns3_server"], CONFIG["gns3_port"], CONFIG["project_id"])
            data = {"nodes": [ \
                {"adapter_number": nodedata[0]["adapter_number"], "node_id": nodedata[0]["node_id"], "port_number": nodedata[0]["port_number"]}, \
                {"adapter_number": nodedata[1]["adapter_number"], "node_id": nodedata[1]["node_id"], "port_number": nodedata[1]["port_number"]}]}
            data_json = json.dumps(data)
            response = requests.post(url, data=data_json, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
            body = response.json()
            if response.status_code == 201:
                print("The link %s has been added between node %s and %s." % (body["link_id"], link["link"][0]["name"], link["link"][1]["name"]))
            else:
                print("Received HTTP error %d when setting the link between node %s and %s! Exiting." % (response.status_code, link["link"][0]["name"], link["link"][1]["name"]))
                exit(1)
        else:
            print("There should be exactly 2 nodes in a link! Exiting.")
            exit(1)

def start_nodes():
    url = "http://%s:%s/v2/projects/%s/nodes/start" % (CONFIG["gns3_server"], CONFIG["gns3_port"], CONFIG["project_id"])
    response = requests.post(url, auth=requests.auth.HTTPBasicAuth(gns3user, gns3pass))
    if response.status_code == 204:
        # Wait 5m for nodes to start booting
        print("Waiting 1 minute for all the nodes to boot properly.")
        time.sleep(60)
    else:
        print("Received HTTP error %d when starting nodes! Exiting." % response.status_code)
        exit(1)

def deploy_baseconfig():
    for node in CONFIG["nodes"]:
        if node["os"] != "none":
            if node["os"] == "junos":
                junos_node = {
                    'device_type': 'generic_telnet',
                    'host': node['console_host'],
                    'port': node['console'],
                    'global_delay_factor': 1
                }
                net_connect = ConnectHandler(**junos_node)
                connected = False
                while connected == False:
                    response = net_connect.find_prompt(delay_factor=5)
                    if response == "login:":
                        print("Starting deployment of the basic configuration on the node %s." % (node['name']))
                        connected = True
                    else:
                        print("The node %s is not ready for configuration. Waiting for 5 seconds to check again." % (node['name']))
                        connected = False
                        time.sleep(5)
                if connected == True:
                    output = net_connect.send_command(
                        command_string="root",
                        expect_string=r"root@:RE",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="cli",
                        expect_string=r"root>",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="configure",
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="set system root-authentication plain-text-password-value Juniper",
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="set system host-name %s" % (node['name']),
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="delete interfaces",
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="set interfaces em1 unit 0 family inet address 169.254.0.2/24",
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="set interfaces em0 unit 0 family inet address %s/%s" % (node['ip'],node['mask']),
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="set routing-options static route 0.0.0.0/0 next-hop %s" % (node['gateway']),
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="set system services ssh root-login allow",
                        expect_string=r"root#",
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="commit",
                        expect_string=r"root@%s#" % (node['name']),
                        strip_prompt=False, strip_command=False
                    )
                    output += net_connect.send_command(
                        command_string="exit",
                        expect_string=r"root@%s>" % (node['name']),
                        strip_prompt=False, strip_command=False
                    )
                print("Configuration of the node %s is complete." % (node['name']))
                net_connect.disconnect()

if __name__ == "__main__":
    # Prompt us er for the GNS3 username and password
    #gns3user = input("Username: ")
    #gns3pass = getpass.getpass()

    gns3user = "admin"
    gns3pass = "gns3"

    ### Loading topology file
    print(">>> Loading topology file")
    with open("config_gns3topology.yml") as config_file:
        CONFIG = yaml.load(config_file, Loader=yaml.FullLoader)

    ### Create project and add its ID to the config
    print(">>> Creating GNS3 project")
    new_project(CONFIG["project_name"])

    ### Add appliance IDs to the config
    print(">>> Retrieving appliance IDs")
    assign_template_id()

    ### Add nodes to the topology
    print(">>> Adding nodes")
    add_nodes()

    ### Apply settings to nodes
    print(">>> Setting nodes")
    set_nodes()

    ### Adding links between nodes
    print(">>> Adding links between nodes")
    add_links()

    ### Starting nodes
    print(">>> Starting all nodes")
    start_nodes()

    ### Deploying basic configuration to nodes
    print(">>> Deploying base configuration")
    deploy_baseconfig()   

    print(">>> Deployment complete")