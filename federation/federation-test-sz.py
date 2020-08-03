#!/usr/bin/env python
import pika, httplib, json, time, ssl
from base64 import b64encode
from argparse import ArgumentParser
import urllib

def send(federation):
    # mp1_ch = pika.BlockingConnection(pika.URLParameters('amqp://rabbitmq:rabbitmq!QAZ@127.0.0.1:15672')).channel() # 87
    # mp2_ch = pika.BlockingConnection(pika.URLParameters('amqp://rabbitmq:rabbitmq!QAZ@127.0.0.1:25672')).channel() # 89

    ''' SSL '''
    context = ssl.create_default_context(cafile="./ca.pem")
    context.load_cert_chain("./cp.pem", "./cp.key")
    ssl_options = pika.SSLOptions(context, "Control Plane Certificate Authority")
    credential = pika.PlainCredentials('rabbitmq', 'rabbitmq!QAZ')
    conn_params = pika.ConnectionParameters(host="127.0.0.1", port=35671, ssl_options=ssl_options, credentials=credential)
    mp1_conn = pika.BlockingConnection(conn_params)
    conn_params = pika.ConnectionParameters(host="127.0.0.1", port=35672, ssl_options=ssl_options, credentials=credential)
    mp2_conn = pika.BlockingConnection(conn_params)


    ''' NOT SSL '''
    # mp1_conn = pika.BlockingConnection(pika.URLParameters('amqp://rabbitmq:rabbitmq!QAZ@127.0.0.1:15672')) # 87
    # mp2_conn = pika.BlockingConnection(pika.URLParameters('amqp://rabbitmq:rabbitmq!QAZ@127.0.0.1:25672')) # 89
    mp1_ch = mp1_conn.channel()
    mp2_ch = mp2_conn.channel()

    print("ex_overlay", "q_scg_test1." + federation.cluster_list[0], "mp1 > mp2")
    mp1_ch.basic_publish("ex_overlay", "q_scg_test1." + federation.cluster_list[0], "mp1 > mp2")
    print("ex_overlay", "q_scg_test1." + federation.current_node, "mp2 > mp1")
    mp2_ch.basic_publish("ex_overlay", "q_scg_test1." + federation.current_node, "mp2 > mp1")
    print("...")
    time.sleep(1)
    print("...")
    time.sleep(1)
    print("...")
    time.sleep(1)

    method_frame, header_frame, salutation = mp1_ch.basic_get("q_scg_test1")
    mp1_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

    method_frame, header_frame, salutation = mp2_ch.basic_get("q_scg_test1")
    mp2_ch.basic_ack(method_frame.delivery_tag)
    print("Notify route: \"%s\"" % (salutation))

def create_exchange(ch, name):
    ch.exchange_declare(name, "direct")

def init_rabbitmq(federation):
    try:
        ''' SSL '''
        context = ssl.create_default_context(cafile="./ca.pem")
        context.load_cert_chain("./cp.pem", "./cp.key")
        ssl_options = pika.SSLOptions(context, "Control Plane Certificate Authority")
        credential = pika.PlainCredentials('rabbitmq', 'rabbitmq!QAZ')
        conn_params = pika.ConnectionParameters(host="127.0.0.1", port=35671, ssl_options=ssl_options, credentials=credential)
        mp1_conn = pika.BlockingConnection(conn_params)
        conn_params = pika.ConnectionParameters(host="127.0.0.1", port=35672, ssl_options=ssl_options, credentials=credential)
        mp2_conn = pika.BlockingConnection(conn_params)

        # mp2_conn = pika.BlockingConnection(pika.URLParameters('amqp://rabbitmq:rabbitmq!QAZ@127.0.0.1:25672')) # 89

        ''' NOT SSL '''
        # mp1_conn = pika.BlockingConnection(pika.URLParameters('amqp://rabbitmq:rabbitmq!QAZ@127.0.0.1:15672')) # 87
        # mp2_conn = pika.BlockingConnection(pika.URLParameters('amqp://rabbitmq:rabbitmq!QAZ@127.0.0.1:25672')) # 89
        mp1_ch = mp1_conn.channel()
        mp2_ch = mp2_conn.channel()
        # create_exchange(mp_ch, "ex_overlay5")
        bind_queue(mp1_ch, "q_scg_test1", "q_scg_test1." + federation.current_node)
        bind_queue(mp2_ch, "q_scg_test1", "q_scg_test1." + federation.cluster_list[0])
    except pika.exceptions.AMQPChannelError as err:
        print("Channel error: {}, stopping...".format(err))

def bind_queue(ch, q_name, bind_name, ex_name = "ex_overlay"):
    ch.queue_declare(q_name)
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
    send(federation)

    # pika.BlockingConnection(pika.URLParameters('amqps://rabbitmq:rabbitmq!QAZ@127.0.0.1:35671?cacertfile=ca.pem&certfile=cp.pem&keyfile=cp.key'))
    # pika.BlockingConnection(pika.URLParameters('amqps://127.0.0.1:35671?cacertfile=ca.pem&certfile=cp.pem&keyfile=cp.key'))

    # context = ssl.create_default_context(cafile="./ca.pem")
    # context.load_cert_chain("./cp.pem", "./cp.key")
    # ssl_options = pika.SSLOptions(context, "Control Plane Certificate Authority")
    # credential = pika.PlainCredentials('rabbitmq', 'rabbitmq!QAZ')
    # conn_params = pika.ConnectionParameters(host="127.0.0.1", port=35671, ssl_options=ssl_options, credentials=credential)
    # mp1_conn = pika.BlockingConnection(conn_params)
