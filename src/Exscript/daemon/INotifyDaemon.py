import os
from lxml                    import etree
from DirWatcher              import monitor
from Order                   import Order
from Exscript.util.decorator import bind

class INotifyDaemon(object):
    def __init__(self,
                 name,
                 directory  = None,
                 queue      = None,
                 processors = None,
                 services   = None):
        self.name       = name
        self.input_dir  = os.path.join(directory, 'in')
        self.output_dir = os.path.join(directory, 'out')
        self.processors = processors
        self.services   = services
        self.queue      = queue
        if not os.path.isdir(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

    def _run_service(self, conn, order):
        print "CONN", conn.get_host().get_name(), order.get_service()
        order.set_status('in-progress')
        service = self.services[order.get_service()]
        service.call(conn)
        #FIXME

    def _save_order(self, order):
        outfile = os.path.join(self.output_dir, order.get_filename())
        order.write(outfile)

    def _on_task_done(self, order):
        print 'Order done:', order.get_id()
        order.set_status('completed')
        self._save_order(order)

    def _on_order_received(self, filename):
        if os.path.basename(filename).startswith('.'):
            return
        print 'Order received:', filename

        # Parse the order.
        try:
            order = Order.from_xml_file(filename)
        except etree.XMLSyntaxError:
            print 'Error: invalid order: ' + filename
            return
        finally:
            os.remove(filename)

        # Read the ID from the filename.
        basename = os.path.basename(filename)
        order.id = os.path.splitext(basename)[0]

        # Enqueue it.
        hosts   = order.get_hosts()
        task    = self.queue.run(hosts, bind(self._run_service, order))
        task.signal_connect('done', self._on_task_done, order)
        order.set_status('queued')
        self._save_order(order)

    def run(self):
        #FIXME: read existing orders on startup.
        print 'Inotify daemon "' + self.name + '" running on ' + self.input_dir
        monitor(self.input_dir, self._on_order_received)