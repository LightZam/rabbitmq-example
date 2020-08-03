#!/usr/bin/env python
import pika, httplib, json, time, ssl
from base64 import b64encode
from argparse import ArgumentParser
import urllib

def send(federation):
    ''' TLS '''
    context = ssl.create_default_context(cafile="./ca.pem")
    context.load_cert_chain("./cp.pem", "./cp.key")
    # ssl_options = pika.SSLOptions(context, "scg.ruckuswireless.com")
    ssl_options = pika.SSLOptions(context, "Control Plane Certificate Authority")
    credential = pika.PlainCredentials('mp', 'mpRabbitmq!QAZ')
    mp1_conn = pika.BlockingConnection(pika.ConnectionParameters(host="172.88.0.2", port=5671, ssl_options=ssl_options, credentials=credential))
    mp2_conn = pika.BlockingConnection(pika.ConnectionParameters(host="172.88.0.3", port=5671, ssl_options=ssl_options, credentials=credential))
    mp3_conn = pika.BlockingConnection(pika.ConnectionParameters(host="172.88.0.4", port=5671, ssl_options=ssl_options, credentials=credential))
    mp4_conn = pika.BlockingConnection(pika.ConnectionParameters(host="172.88.0.5", port=5671, ssl_options=ssl_options, credentials=credential))

    ''' NOT STL '''
    # mp1_ch = pika.BlockingConnection(pika.URLParameters('amqp://%s:%s@%s:%s' % ("mp", "mpRabbitmq!QAZ", federation.current_node, federation.rabbitmq_port))).channel()
    # mp2_ch = pika.BlockingConnection(pika.URLParameters('amqp://%s:%s@%s:%s' % ("mp", "mpRabbitmq!QAZ", federation.cluster_list[0], federation.rabbitmq_port))).channel()
    # mp3_ch = pika.BlockingConnection(pika.URLParameters('amqp://%s:%s@%s:%s' % ("mp", "mpRabbitmq!QAZ", federation.cluster_list[1], federation.rabbitmq_port))).channel()
    # mp4_ch = pika.BlockingConnection(pika.URLParameters('amqp://%s:%s@%s:%s' % ("mp", "mpRabbitmq!QAZ", federation.cluster_list[2], federation.rabbitmq_port))).channel()

    # mp1_ch = pika.BlockingConnection(pika.ConnectionParameters(federation.current_node, federation.rabbitmq_port, headers=federation.headers)).channel()
    # mp2_ch = pika.BlockingConnection(pika.ConnectionParameters(federation.cluster_list[0], federation.rabbitmq_port)).channel()
    # mp3_ch = pika.BlockingConnection(pika.ConnectionParameters(federation.cluster_list[1], federation.rabbitmq_port)).channel()
    # mp4_ch = pika.BlockingConnection(pika.ConnectionParameters(federation.cluster_list[2], federation.rabbitmq_port)).channel()

    mp1_ch = mp1_conn.channel()
    mp2_ch = mp2_conn.channel()
    mp3_ch = mp3_conn.channel()
    mp4_ch = mp4_conn.channel()

    mp1_ch.basic_publish("ex_overlay", "q_scg_ccd." + federation.cluster_list[0], "ccd: mp1 > mp2")
    mp1_ch.basic_publish("ex_overlay", "q_scg_ccd." + federation.cluster_list[1], "ccd: mp1 > mp3")
    mp1_ch.basic_publish("ex_overlay", "q_scg_ccd." + federation.cluster_list[2] , "ccd: mp1 > mp4")

    mp2_ch.basic_publish("ex_overlay", "q_scg_ccd." + federation.current_node, "ccd: mp2 > mp1")
    mp3_ch.basic_publish("ex_overlay", "q_scg_ccd." + federation.current_node, "ccd: mp3 > mp1")
    mp4_ch.basic_publish("ex_overlay", "q_scg_ccd." + federation.current_node, "ccd: mp4 > mp1")

    mp4_ch.basic_publish("ex_overlay", "q_scg_md." + federation.current_node, "md: mp4 > mp1")

    print("...")
    time.sleep(1)
    print("...")
    time.sleep(1)
    print("...")
    time.sleep(1)

    method_frame, header_frame, salutation = mp1_ch.basic_get("q_scg_ccd")
    mp1_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

    method_frame, header_frame, salutation = mp1_ch.basic_get("q_scg_ccd")
    mp1_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

    method_frame, header_frame, salutation = mp1_ch.basic_get("q_scg_ccd")
    mp1_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

    method_frame, header_frame, salutation = mp2_ch.basic_get("q_scg_ccd")
    mp2_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

    method_frame, header_frame, salutation = mp3_ch.basic_get("q_scg_ccd")
    mp3_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

    method_frame, header_frame, salutation = mp4_ch.basic_get("q_scg_ccd")
    mp4_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

    # method_frame, header_frame, salutation = mp1_ch.basic_get("q_scg_md")
    # mp1_ch.basic_ack(method_frame.delivery_tag)
    # print("Notify route: \"%s\"" % (salutation))

def create_exchange(ch, name):
    ch.exchange_declare(name, "direct")

def init_rabbitmq(federation):
    try:

        ''' TLS '''
        context = ssl.create_default_context(cafile="./mq.pem")
        context.load_cert_chain("./mq.pem", "./mq.key")
        ssl_options = pika.SSLOptions(context, "scg.ruckuswireless.com")
        credential = pika.PlainCredentials('rabbitmq', 'rabbitmq!PASS')
        mp1_conn = pika.BlockingConnection(pika.ConnectionParameters(host="35.229.135.255", port=5671, ssl_options=ssl_options, credentials=credential))

        mp1_ch = mp1_conn.channel()
        # create_exchange(mp_ch, "ex_overlay5")
        bind_queue(mp1_ch, "q_scg_ccd", "q_scg_ccd." + federation.current_node)
        # bind_queue(mp1_ch, "q_scg_md", "q_scg_md." + federation.current_node)
        print("finish bind queue: ", federation.cluster_list)
    except pika.exceptions.AMQPChannelError as err:
        print("Channel error: {}, stopping...".format(err))
    except Exception as err:
        print("Error...", err)

def bind_queue(ch, q_name, bind_name, ex_name = "ex_overlay"):
    # ch.queue_declare(q_name)
    ch.queue_bind(q_name, ex_name, bind_name)

def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument("-c", "--current_node", dest="current_node")
    parser.add_argument("-l", "--cluster-list", dest="cluster_list", nargs="*")
    args = parser.parse_args()

    if not args.current_node:
        print("Warn: Not assign current_node")
        return

    if not args.cluster_list:
        print("Warn: Not assign any cluster list")
        return

    return Federation(args.current_node, args.cluster_list)

class Federation:
    def __init__(self, current_node, cluster_list):
        self.current_node = current_node
        self.cluster_list = filter(lambda x: x != current_node, cluster_list)
        self.rabbitmq_management_port = 8672
        self.rabbitmq_port = 5672
        self.headers = {
            "Authorization": "Basic %s" % b64encode("rabbitmq:rabbitmq!QAZ")
        }

# main
if (__name__ == "__main__"):
    federation = parse_arguments()
    init_rabbitmq(federation)
    # send(federation)