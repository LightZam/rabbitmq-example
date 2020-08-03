#!/usr/bin/env python
import httplib, json, logging, os, time
from base64 import b64encode
from argparse import ArgumentParser

def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument("-c", "--current_node", dest="current_node")
    parser.add_argument("-l", "--cluster_list", dest="cluster_list", nargs="*")
    args = parser.parse_args()

    if not args.current_node:
        logging.error("Error: Not assign current_node")
        return

    if not args.cluster_list:
        logging.warn("Warn: Not assign any cluster list")
        return Federation(args.current_node, [])

    return Federation(args.current_node, args.cluster_list)

class Federation:
    def __init__(self, current_node, cluster_list):
        self.current_node = current_node
        self.cluster_list = filter(lambda x: x != current_node, cluster_list)
        self.rabbitmq_port = 5672
        # self.ep = "127.0.0.1:8672"
        self.ep = "%s:8672" % self.current_node
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic cmFiYml0bXE6cmFiYml0bXEhUUFa"
        }

    def execute(self):
        try:
            upstreams = self.get_upstreams()

            # print(upstreams, self.current_node, self.cluster_list)
            if not upstreams:
                logging.debug("join all: %s => %s; mq list: %s" % (self.current_node, self.cluster_list, upstreams))
                self.join_all(self.current_node, self.cluster_list)
            else:
                mq_node_list = map(lambda x: x["name"].replace("%s-" % self.current_node, ""), upstreams)
                print(mq_node_list)
                removed_items = set(mq_node_list) - set(self.cluster_list)
                added_items = set(self.cluster_list) - set(mq_node_list)

                # ip change, remove old ip setting
                if removed_items and added_items:
                    self.reform_when_ip_changed(self.current_node, added_items.pop(), removed_items.pop(), mq_node_list)
                # remove action
                elif removed_items:
                    self.remove(self.current_node, removed_items.pop())
                # join action
                elif added_items:
                    self.join(self.current_node, added_items.pop())
            return True
        except:
            logging.error("Fail to build mesh network", exc_info=True)
            return False

    def reform_when_ip_changed(self, current_node, new_target, removed_target, mq_node_list):
        logging.info("action: ip changed")
        self.join(current_node, new_target)
        self.remove(current_node, removed_target)
        self.remove_all(removed_target, mq_node_list)

    def join_all(self, current_node, cluster_list):
        for node in cluster_list:
            self.join(current_node, node)

    def join(self, current_node, new_target):
        upstream_name = self.get_upstream_name(current_node, new_target)
        logging.info("join to mesh network: %s" % upstream_name)
        ca = '/opt/ruckuswireless/wsg/ssl/ca/ca.pem'
        cp_pem = '/opt/ruckuswireless/wsg/ssl/server/server.pem'
        cp_key = '/opt/ruckuswireless/wsg/ssl/server/server.key'
        # uri = "amqps://mp:mpRabbitmq!QAZ@%s:%s?cacertfile=%s&certfile=%s&keyfile=%s&verify=verify_peer&server_name_indication=%s" % (new_target, 5671, ca, cp_pem, cp_key, "scg.ruckuswireless.com")
        # uri = "amqps://mp:mpRabbitmq!QAZ@%s:%s?cacertfile=%s&certfile=%s&keyfile=%s&verify=verify_peer&server_name_indication=%s" % (new_target, 5671, ca, cp_pem, cp_key, "Control Plane Certificate Authority")
        # uri = "amqps://mp:mpRabbitmq!QAZ@%s:%s?cacertfile=%s&certfile=%s&keyfile=%s&verify=verify_none&server_name_indication=%s" % (new_target, 5671, ca, cp_pem, cp_key, "scg.ruckuswireless.com")
        uri = "amqps://mp:mpRabbitmq!QAZ@%s:%s?verify=verify_none" % (new_target, 5671)
        # uri = "amqps://mp:mpRabbitmq!QAZ@%s:%s" % (new_target, 5671)
        # uri = "amqps://mp:mpRabbitmq!QAZ@%s:%s?verify=verify_peer&server_name_indication=Control Plane Certificate Authority" % (new_target, 5671)

        # uri = "amqp://mp:mpRabbitmq!QAZ@%s:%s" % (new_target, self.rabbitmq_port)
        self.upsert_policy("connect_to_all_upstreams")
        self.upsert_upstream(upstream_name, {"uri": uri, "expires": 3600000})

    def remove_all(self, current_node, mq_node_list):
        for node in mq_node_list:
            self.remove(current_node, node)

    def remove(self, current_node, remove_target):
        logging.info("remove from mesh network: %s,,,,,%s" % (current_node, remove_target))
        upstream_name = self.get_upstream_name(current_node, remove_target)
        logging.info("remove from mesh network: %s" % upstream_name)
        self.delete_upstream(upstream_name)

    def get_upstream_name(self, current_node, target_node):
        return "%s-%s" % (current_node, target_node)

    def upsert_upstream(self, name, params):
        conn = httplib.HTTPConnection(self.ep)

        try:
            requestURL = "http://%s/api/parameters/federation-upstream/%%2f/%s" % (self.ep, name)
            logging.info("PUT - %s, %s" % (requestURL, json.dumps({"value": params})))
            conn.request("PUT", requestURL, json.dumps({"value": params}), self.headers)
            resp = conn.getresponse()
            if resp.status != 200 and resp.status != 201:
                raise Exception("PUT - %s: %s, %s" % (requestURL, resp.status, resp.reason))
            return resp.read()
        finally:
            conn.close()

    def delete_upstream(self, name):
        conn = httplib.HTTPConnection(self.ep)

        try:
            requestURL = "http://%s/api/parameters/federation-upstream/%%2f/%s" % (self.ep, name)
            logging.info("DELETE - %s" % requestURL)
            conn.request("DELETE", requestURL, "", self.headers)
            resp = conn.getresponse()
            if resp.status != 200 and resp.status != 204:
                raise Exception("DELETE - %s: %s, %s" % (requestURL, resp.status, resp.reason))
            return resp.read()
        finally:
            conn.close()

    def get_upstreams(self):
        conn = httplib.HTTPConnection(self.ep)

        try:
            requestURL = "http://%s/api/parameters/federation-upstream/%%2f" % (self.ep)
            logging.info("GET - %s" % requestURL)
            conn.request("GET", requestURL, "", self.headers)
            resp = conn.getresponse()
            if resp.status == 200:
                response_body = resp.read()
                if not response_body:
                    return []
                else:
                    return json.loads(response_body)
            else:
                raise Exception("GET - %s: %s, %s" % (requestURL, resp.status, resp.reason))
        finally:
            conn.close()

    def upsert_policy(self, name, params = {"pattern":"ex_overlay", "definition": {"federation-upstream-set": "all"}, "apply-to":"exchanges"}):
        conn = httplib.HTTPConnection(self.ep)

        try:
            requestURL = "http://%s/api/policies/%%2f/%s" % (self.ep, name)
            conn.request("PUT", requestURL, json.dumps(params), self.headers)
            resp = conn.getresponse()
            resp_body = resp.read()
            return resp_body
        finally:
            conn.close()

def init_logging():
    if not os.path.exists("/data/log/rabbitmq"):
        os.mkdir("/data/log/rabbitmq")
    logging.basicConfig(filename="/data/log/rabbitmq/federationmq.log", level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# main
if (__name__ == "__main__"):
    init_logging()
    retry_times = 60
    federation = parse_arguments()
    # retry 60 times = 30*60 = 30 mins
    for i in range(retry_times):
        # if os.path.isfile("/data/log/rabbitmq.pid"):
        if federation.execute():
            break
        time.sleep(1)
        logging.info("Retring to build mesh network...")