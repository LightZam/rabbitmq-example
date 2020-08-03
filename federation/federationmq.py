#!/usr/bin/env python
import httplib, json, logging, os, time, sys
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

class Federation(WSG3rdNonJavaCmd):
    def __init__(self, current_node, cluster_list):
        WSG3rdNonJavaCmd.__init__(self, run_at_dir, exec_at_dir)
        self.config_file = self.getCommonConfigFile("rabbitmq")
        self.initVars()
        self.current_node = current_node
        self.cluster_list = filter(lambda x: x != current_node, cluster_list)
        self.ep = "%s:%s" % (self.ERL_EPMD_ADDRESS, self.RABBITMQ_MANAGEMENT_PORT)
        self.headers = {
            "Content-Type": "application/json",
            # rabbitmq:rabbitmq!ZAM
            "Authorization": "Basic cmFiYml0bXE6cmFiYml0bXEhWkFN"
        }
        self.SSL_OPTIONS = "cacertfile=%s&certfile=%s&keyfile=%s&verify=verify_peer&server_name_indication=%s" % (self.RABBITMQ_TLS_CA, self.RABBITMQ_TLS_CERT, self.RABBITMQ_TLS_KEY, self.RABBITMQ_TLS_SERVER_NAME_INDICATION)

    def initVars(self):
        self.initCommVars()
        self.RABBITMQ_MANAGEMENT_PORT = "15672"
        self.RABBITMQ_TLS_PORT = "5671"
        self.RABBITMQ_TLS_VERIFY = "verify_peer"
        self.RABBITMQ_TLS_SERVER_NAME_INDICATION = "mq.zamhuang.tw"
        self.RABBITMQ_TLS_FAIL_IF_NO_PEER_CERT = "true"
        self.RABBITMQ_TLS_CA = "/opt/rabbitmq/ca_certificate.pem"
        self.RABBITMQ_TLS_CERT = "/opt/rabbitmq/client_certificate.pem"
        self.RABBITMQ_TLS_KEY = "/opt/rabbitmq/client_key.pem"
        self.ERL_EPMD_ADDRESS = "127.0.0.1"

    def execute(self):
        try:
            upstreams = self.get_upstreams()

            if not upstreams:
                logging.debug("join all: %s => %s; mq list: %s" % (self.current_node, self.cluster_list, upstreams))
                self.join_all(self.current_node, self.cluster_list)
            else:
                mq_node_list = map(lambda x: x["name"].replace("%s-" % self.current_node, ""), upstreams)
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
        uri = "amqps://mp:mpRabbitmq!QAZ@%s:%s?%s" % (new_target, self.RABBITMQ_TLS_PORT, self.SSL_OPTIONS)
        self.upsert_upstream(upstream_name, {"uri": uri, "expires": 3600000})

    def remove_all(self, current_node, mq_node_list):
        for node in mq_node_list:
            self.remove(current_node, node)

    def remove(self, current_node, remove_target):
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

def init_logging():
    if not os.path.exists("/data/log/rabbitmq"):
        os.mkdir("/data/log/rabbitmq")
    logging.basicConfig(filename="/data/log/rabbitmq/federationmq.log", level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# main
if (__name__ == "__main__"):
    init_logging()
    federation = parse_arguments()
    federation.execute()