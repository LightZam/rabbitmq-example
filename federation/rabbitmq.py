#!/bin/env python
import os, sys, time
import getopt, json

exec_at_dir = os.getcwd()
exec_file = sys.argv[0]
if os.path.islink(exec_file):
    exec_file = os.path.realpath(exec_file)
os.chdir(os.path.dirname(exec_file))
run_at_dir = os.getcwd()

if run_at_dir not in sys.path: sys.path.append(run_at_dir)
if run_at_dir+'/../lib' not in sys.path: sys.path.append(run_at_dir+'/../lib')

import libcommon, libresourcemanager
from libresourcemanager import *
from libcommon import *

from libwsgcmd.libwsg3rdnonjavacmd import WSG3rdNonJavaCmd


class RabbitMQ(WSG3rdNonJavaCmd):
    def __init__(self, run_at_dir, exec_at_dir):
        WSG3rdNonJavaCmd.__init__(self, run_at_dir, exec_at_dir)
        self.exec_file = self.getExecfile()
        self.app_name = self.getAppname()
        self.config_file = self.getCommonConfigFile(self.app_name)
        self.account_type = 'admin'
        self.initVars()

    def initVars(self):
        self.initCommVars()
        self.MAX_FILE_OPEN = self.getAttr(self.config_file, 'MAX_FILE_OPEN')
        self.LOG_PATH = self.getAttr(self.config_file, 'LOG_PATH')
        self.PID_FILE = self.getAttr(self.config_file, 'PID_FILE')
        self.ENABLED_PLUGINS_FILE = self.getAttr(self.config_file, 'ENABLED_PLUGINS_FILE')
        self.RABBITMQ_MNESIA_DIR = self.getAttr(self.config_file, 'RABBITMQ_MNESIA_DIR')
        self.RABBITMQ_DIST_PORT = self.getAttr(self.config_file, 'RABBITMQ_DIST_PORT')
        self.RABBITMQ_COOKIE = self.getAttr(self.config_file, 'RABBITMQ_COOKIE')
        self.RABBITMQ_INIT_FILE = self.getAttr(self.config_file, 'RABBITMQ_INIT_FILE')
        self.RABBITMQ_CONF_FILE = self.getAttr(self.config_file, 'RABBITMQ_CONF_FILE')
        self.RABBITMQ_ADDRESS = self.getAttr(self.config_file, 'RABBITMQ_ADDRESS')
        self.RABBITMQ_PORT = self.getAttr(self.config_file, 'RABBITMQ_PORT')
        self.ERL_EPMD_ADDRESS = self.getAttr(self.config_file, 'ERL_EPMD_ADDRESS')
        self.get_hostname()

        ## MP-CP Configuration
        self.RABBITMQ_USERS = self.getAttr(self.config_file, 'USERS')
        self.RABBITMQ_EXCHANGE_LIST = self.getAttr(self.config_file, 'EXCHANGE')
        self.RABBITMQ_QUEUE_LIST = self.getAttr(self.config_file, 'QUEUE')
        self.RABBITMQ_BINDING_LIST = self.getAttr(self.config_file, 'BINDING')
        self.RABBITMQ_POLICIES_LIST = self.getAttr(self.config_file, 'POLICIES')

        self.clean_data = False

        self.extra_message = self.extra_message + """
  ./__exec_file__ list_queues
        """

    def get_hostname(self):
        self.RABBITMQ_HOSTNAME_FILE = self.getAttr(self.config_file, 'RABBITMQ_HOSTNAME_FILE')
        if os.path.exists(self.RABBITMQ_HOSTNAME_FILE):
            command = "cat " + self.RABBITMQ_HOSTNAME_FILE
            self.RABBITMQ_HOSTNAME = str(libcommon.SystemTools.runCmd(command, return_message=True, print_message=False))
        else:
            command = "head -1 /etc/hosts  | awk -F ' ' '{ print $2}'"
            self.RABBITMQ_HOSTNAME = str(libcommon.SystemTools.runCmd(command, return_message=True, print_message=False))
            config_file = open(self.RABBITMQ_HOSTNAME_FILE, 'wb')
            config_file.write(self.RABBITMQ_HOSTNAME)
            config_file.close()
        ## Fix the RabbitMQ node name because we don't need RabbitMQ Clustering
        self.RABBITMQ_CTL = 'RABBITMQ_NODENAME=rabbit@localhost HOSTNAME=%s HOME=%s ./rabbitmqctl ' % (self.RABBITMQ_HOSTNAME, self.RABBITMQ_COOKIE)

    ## override pre_start()
    def pre_start(self):
        ## Check rabbitmq log folder
        if not os.path.exists(self.LOG_PATH):
            os.makedirs(self.LOG_PATH)
        ## Enable RabbitMQ management plug-in
        with open(self.ENABLED_PLUGINS_FILE, 'w') as plugin_file:
            plugin_file.write('[rabbitmq_federation, rabbitmq_federation_management].\n')
        self.init_rabbitmq_intf()
        self.create_rabbitmq_init_file()

    def init_rabbitmq_intf(self):
        intf = self.RABBITMQ_ADDRESS + ":" + self.RABBITMQ_PORT
        command = "/usr/bin/sed -i -E 's/(listeners.tcp.local .*=)(.*)/\\1 " + intf + "/g'" + " " + self.RABBITMQ_CONF_FILE
        libcommon.SystemTools.runCmd(command, return_message=False, print_message=False)
        command = "/usr/bin/sed -i -E 's/^(loopback_users.(cp|mp) = true)/#\\1/g'" + " " + self.RABBITMQ_CONF_FILE
        libcommon.SystemTools.runCmd(command, return_message=False, print_message=False)

    def create_rabbitmq_init_file(self):
        ## The MD queue init code will remove after 6.0 because the MD queue will dynamically be created
        command = "cat " + self.CLUSTER_PROPERTY_FILE + " | grep 'blade.id' | awk -F '=' '{print $2}'"
        blade_id = str(libcommon.SystemTools.runCmd(command, return_message=True, print_message=False))
        MD_QUEUE_ID = "q_md_" + blade_id
        ## Preprocess MD setting
        if self.RABBITMQ_QUEUE_LIST.get('q_md', 'amq.') != 'amq.':
            self.RABBITMQ_QUEUE_LIST[MD_QUEUE_ID] = self.RABBITMQ_QUEUE_LIST.pop('q_md')

        for exchange_name, dests in self.RABBITMQ_BINDING_LIST.iteritems():
            for dest in dests:
                if dest.get('destination', 'amq.') == 'q_md':
                    dest['destination'] = MD_QUEUE_ID
                if dest.get('routing_key', 'amq.') == 'q_md':
                    dest['routing_key'] = MD_QUEUE_ID


        rabbimq_definitions = {'users':[], "vhosts": [{"name": "/"}], 'permissions':[], 'exchanges':[], 'queues':[], 'bindings':[], 'policies':[]}
        ## Create default RabbitMQ users
        for user_name, parms in self.RABBITMQ_USERS.iteritems():
            user = dict()
            user['name'] = user_name
            for k, v in parms.iteritems():
                user[k] = v
            rabbimq_definitions['users'].append(user)

        ## Set permission for user
        for user_name, parms in self.RABBITMQ_USERS.iteritems():
            user_permission = {'vhost': '/', 'configure': '', 'write': '.*', 'read': '.*'}
            user_permission['user'] = user_name
            if user_name == 'rabbitmq':
                user_permission['configure'] = ".*"
            elif user_name == 'mp':
                user_permission['configure'] = "^q_scg_collectd$"
            elif user_name == 'cp':
                user_permission['configure'] = "^(q_scg_ccm_server.*|q_md.*)"
            else:
                user_permission['configure'] = ""
            rabbimq_definitions['permissions'].append(user_permission)

        ## Create exchange
        for exchange_name, parms in self.RABBITMQ_EXCHANGE_LIST.iteritems():
            mpcp_exchange = {'vhost': '/', 'type': 'direct', 'durable': False, 'auto_delete': False, 'internal': False, 'arguments': {}}
            mpcp_exchange['name'] = exchange_name
            for k, v in parms.iteritems():
                if k in ['type', 'durable', 'auto_delete', 'internal']:
                    mpcp_exchange[k] = v
                else:
                    mpcp_exchange['arguments'][k] = v
            rabbimq_definitions['exchanges'].append(mpcp_exchange)

        ## Create queue
        for queue_name, parms in self.RABBITMQ_QUEUE_LIST.iteritems():
            mpcp_queue = {'vhost': '/', 'durable': False, 'auto_delete': False, 'arguments': {}}
            mpcp_queue['name'] = queue_name
            for k, v in parms.iteritems():
                if k in ['durable', 'auto_delete']:
                    mpcp_queue[k] = v
                else:
                    mpcp_queue['arguments'][k] = v
            rabbimq_definitions['queues'].append(mpcp_queue)

        ## Binding exchange and queue
        for exchange_name, dests in self.RABBITMQ_BINDING_LIST.iteritems():
            control_interface = self.system_tools.runCmd('gd rks-nettools get if ControlInterface', return_message=True)
            control_interface_mac = self.system_tools.runCmd('gd rks-nettools get mac ' + control_interface, return_message=True)
            for dest in dests:
                mpcp_binding = {'source': exchange_name, 'vhost': '/', 'arguments': {}}
                for k, v in dest.iteritems():
                    if '{controlInterfaceMac}' in v:
                        mpcp_binding[k] = v.replace('{controlInterfaceMac}', control_interface_mac.upper())
                    else:
                        mpcp_binding[k] = v
                rabbimq_definitions['bindings'].append(mpcp_binding)

        ## Create policies
        for policy_name, parms in self.RABBITMQ_POLICIES_LIST.iteritems():
            mpcp_policy = {'vhost': '/', 'definition': {}}
            mpcp_policy['name'] = policy_name
            for k, v in parms.iteritems():
                if k in ['pattern', 'apply-to', 'priority']:
                    mpcp_policy[k] = v
                else:
                    mpcp_policy['definition'][k] = v
            rabbimq_definitions['policies'].append(mpcp_policy)

        with open(self.RABBITMQ_INIT_FILE, 'w') as init_file:
            init_file.write(json.dumps(rabbimq_definitions, indent=4))
            init_file.write("\n")

    # post_start is workaround and remove after MD pass
    ## override post_start()
    def post_start(self):
        time.sleep(10)

    ## override getStartCmd()
    def getStartCmd(self):
        ## Fix the RabbitMQ node name because we don't need RabbitMQ Clustering
        return 'ulimit -n %s && HOSTNAME=%s RABBITMQ_PID_FILE=%s RABBITMQ_MNESIA_BASE=%s RABBITMQ_LOG_BASE=%s ' \
               'RABBITMQ_ENABLED_PLUGINS_FILE=%s RABBITMQ_DIST_PORT=%s RABBITMQ_NODENAME=rabbit@localhost HOME=%s ERL_EPMD_ADDRESS=%s ' \
               './rabbitmq-server &' \
               % (self.MAX_FILE_OPEN, self.RABBITMQ_HOSTNAME, self.PID_FILE, self.RABBITMQ_MNESIA_DIR, self.LOG_PATH,
                  self.ENABLED_PLUGINS_FILE, self.RABBITMQ_DIST_PORT,
                  self.RABBITMQ_COOKIE, self.ERL_EPMD_ADDRESS)

    ## override getFilterString()
    def getFilterString(self):
        return 'rabbitmq-server'

    ## override do_stop()
    def do_stop(self, force_kill_after_timeout=True):
        os.chdir(self.HOME_DIR)
        self.display("Stop server...")
        if self.bForceKill:
            self.forceStop()
        else:
            command = self.RABBITMQ_CTL + 'shutdown'
            self.debug(command)
            self.debug(str(libcommon.SystemTools.runCmd(command, True)))
            command = 'epmd -kill'
            self.debug(command)
            self.debug(str(libcommon.SystemTools.runCmd(command, True)))
            libresourcemanager.delAppPid(self.PID_FILE)
            time.sleep(self.first_time_wait_sec)
            sec_wait_for_stop = 0
            while not self.getSkipWaitFlag() and not self.isDown():
                print "Wait for %s down...(%s/%s)" % (self.display_name, sec_wait_for_stop, self.MAX_SEC_WAIT_FOR_STOP)
                if force_kill_after_timeout and self.MAX_SEC_WAIT_FOR_STOP <= sec_wait_for_stop:
                    print "Exceed max seconds (%s) for waiting process stop!" % self.MAX_SEC_WAIT_FOR_STOP
                    self.bThreadDump = True
                    self.forceStop()
                else:
                    time.sleep(self.sleep_sec)
                    sec_wait_for_stop += self.sleep_sec

        if self.clean_data:
            self.display("Clear RabbitMQ Database")
            command = "rm -rf %s/rabbit\@*" % self.RABBITMQ_MNESIA_DIR
            self.system_tools.runCmd(command, on_error_exit=False)
            self.display("Clear RabbitMQ Log")
            command = "rm -rf %s/rabbit\@*" % self.LOG_PATH
            self.system_tools.runCmd(command, on_error_exit=False)

    ## override libwsgcmd.forceStop() to force stop RabbitMQ
    def forceStop(self):
        command = "killall -I rabbitmq-server"
        message = "Force kill process (%s)! [%s]" % (self.getAppname(), command)
        self.debug(message)
        self.logCommandHistory(message)
        libcommon.execute_external_commands(command, self.logger)

    ## override status()
    def status(self, force_kill_after_timeout=True):
        os.chdir(self.HOME_DIR)
        command = self.RABBITMQ_CTL + 'status'
        self.debug(command)
        print str(libcommon.SystemTools.runCmd(command, True))

    def list_queues(self, force_kill_after_timeout=True):
        os.chdir(self.HOME_DIR)
        command = self.RABBITMQ_CTL + 'list_queues'
        self.debug(command)
        print str(libcommon.SystemTools.runCmd(command, True))

    def doLocalOption(self):
        argv = sys.argv
        try:
            opts, args = getopt.getopt(argv[1:], self.commAllowOptStr + "c",
                                       self.commAllowOptArray + \
                                       ["clear"]
                                       )
            for o, a in opts:
                if o in ("-c", "--clear"):
                    self.clean_data = True
                    sys.argv.remove(o)
                else:
                    pass
        except getopt.GetoptError, err:
            print err
            self.showUsage()
            exit(1)
            pass

    def doLocalAction(self):
        argv = sys.argv
        if len(argv) < 2:
            return
        try:
            if argv[1] == 'list_queues':
                self.list_queues()
                exit(0)
        except Exception as err:
            print err
            self.showUsage()
            exit(1)

    def run(self):
        if libresourcemanager.checkPropertyFile(self.CLUSTER_PROPERTY_FILE):
            ## do local option
            self.doLocalOption()
            self.doLocalAction()
            ## do option
            self.doOption()
            ## do action
            self.doAction()
        else:
            if '-s' not in sys.argv:
                print "cluster property check fail, exit program!"
            exit(5)


from scgstd.decorator.profile import profiler
@profiler('/data/profiles/%s' % os.path.basename(sys.argv[0]).replace('.py','.profile'))
def main():
    rabbitmq = RabbitMQ(run_at_dir, exec_at_dir)
    rabbitmq.run()

if __name__ == "__main__":
    main()
