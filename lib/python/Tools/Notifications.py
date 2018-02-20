from datetime import datetime
from Tools.BoundFunction import boundFunction
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN

notifications = []
notificationAdded = []
current_notifications = []

class NotificationQueueEntry:

    def __init__(self, fnc, screen, id, *args, **kwargs):
        self.timestamp = datetime.now()
        self.pending = True
        self.fnc = fnc
        self.screen = screen
        self.id = id
        self.args = args
        self.kwargs = kwargs
        self.domain = 'default'
        if kwargs.has_key('domain'):
            if kwargs['domain']:
                if kwargs['domain'] in notificationQueue.domains:
                    self.domain = kwargs['domain']
                else:
                    print '[NotificationQueueEntry] WARNING: domain', kwargs['domain'], 'is not registred in notificationQueue!'
            del kwargs['domain']
        if kwargs.has_key('deferred_callable'):
            if kwargs['deferred_callable']:
                self.deferred_callable = kwargs['deferred_callable']
            del kwargs['deferred_callable']
        else:
            self.deferred_callable = notificationQueue.domains[self.domain]['deferred_callable']
        if kwargs.has_key('text'):
            self.text = kwargs['text']
        elif len(args) and isinstance(args, tuple) and isinstance(args[0], basestring):
            self.text = args[0]
        else:
            self.text = screen.__name__


def isPendingOrVisibleNotificationID(id):
    q = notificationQueue
    return q.isVisibleID(id) or q.isPendingID(id)

def __AddNotification(fnc, screen, id, *args, **kwargs):
    if ".MessageBox'>" in `screen`:
        kwargs['simple'] = True
    if ".Standby'>" in `screen`:
        removeCIdialog()
    notifications.append((fnc,
     screen,
     args,
     kwargs,
     id))
    for x in notificationAdded:
        x()


def AddNotification(screen, *args, **kwargs):
    AddNotificationWithCallback(None, screen, *args, **kwargs)


def AddNotificationWithCallback(fnc, screen, *args, **kwargs):
    __AddNotification(fnc, screen, None, *args, **kwargs)


def AddNotificationParentalControl(fnc, screen, *args, **kwargs):
    RemovePopup('Parental control')
    __AddNotification(fnc, screen, 'Parental control', *args, **kwargs)


def AddNotificationWithID(id, screen, *args, **kwargs):
    __AddNotification(None, screen, id, *args, **kwargs)


def RemovePopup(id):
    print 'RemovePopup, id =', id
    for x in notifications:
        if x[4] and x[4] == id:
            print '(found in notifications)'
            notifications.remove(x)

    for x in current_notifications:
        if x[0] == id:
            print '(found in current notifications)'
            x[1].close()


from Screens.MessageBox import MessageBox

def AddPopup(text, type, timeout, id = None):
    if id is not None:
        RemovePopup(id)
    print 'AddPopup, id =', id
    AddNotificationWithID(id, MessageBox, text=text, type=type, timeout=timeout, close_on_any_key=True)


def removeCIdialog():
    import NavigationInstance
    if NavigationInstance.instance and NavigationInstance.instance.wasTimerWakeup():
        import Screens.Ci
        for slot in Screens.Ci.CiHandler.dlgs:
            if hasattr(Screens.Ci.CiHandler.dlgs[slot], 'forceExit'):
                Screens.Ci.CiHandler.dlgs[slot].tag = 'WAIT'
                Screens.Ci.CiHandler.dlgs[slot].forceExit()

ICON_DEFAULT = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/marker.png'))
ICON_MAIL = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/notification_mail.png'))
ICON_TIMER = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/clock.png'))

class NotificationQueue:

    def __init__(self):
        self.queue = []
        self.__screen = None
        self.current = []
        self.addedCB = []
        self.domains = {'default': {'name': _('unspecified'),
                     'icon': ICON_DEFAULT,
                     'deferred_callable': False}}

    def registerDomain(self, key, name, icon = ICON_DEFAULT, deferred_callable = False):
        if key not in self.domains:
            self.domains[key] = {'name': name,
             'icon': icon,
             'deferred_callable': deferred_callable}

    def addEntry(self, entry):
        self.queue.append(entry)
        for x in self.addedCB:
            x()

    def isPendingID(self, id):
        for entry in self.queue:
            if entry.pending and entry.id == id:
                return True

        return False

    def isVisibleID(self, id):
        for entry, dlg in self.current:
            if entry.id == id:
                return True

        return False

    def removeSameID(self, id):
        for entry in self.queue:
            if entry.pending and entry.id == id:
                print '(found in notifications)'
                self.queue.remove(entry)

        for entry, dlg in self.current:
            if entry.id == id:
                print '(found in current notifications)'
                dlg.close()

    def getPending(self, domain = None):
        res = []
        for entry in self.queue:
            if entry.pending and (domain == None or entry.domain == domain):
                res.append(entry)

        return res

    def popNotification(self, parent, entry = None):
        if entry:
            performCB = entry.deferred_callable
        else:
            pending = self.getPending()
            if len(pending):
                entry = pending[0]
            else:
                return
            performCB = True
        print '[NotificationQueue::popNotification] domain', entry.domain, 'deferred_callable:', entry.deferred_callable
        if performCB and entry.kwargs.has_key('onSessionOpenCallback'):
            entry.kwargs['onSessionOpenCallback']()
            del entry.kwargs['onSessionOpenCallback']
        entry.pending = False
        if performCB and entry.fnc is not None:
            dlg = parent.session.openWithCallback(entry.fnc, entry.screen, *entry.args, **entry.kwargs)
        else:
            dlg = parent.session.open(entry.screen, *entry.args, **entry.kwargs)
        d = (entry, dlg)
        self.current.append(d)
        dlg.onClose.append(boundFunction(self.__notificationClosed, d))

    def __notificationClosed(self, d):
        self.current.remove(d)


notificationQueue = NotificationQueue()
