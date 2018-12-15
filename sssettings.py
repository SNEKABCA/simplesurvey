from qt5pick import QtCore

class SSSettings(QtCore.QSettings):

    def __init__ (self, *args, **kwargs):
        super(SSSettings,self).__init__(*args, **kwargs)

    def value(self, key, defaultvalue = None):
        value = super(SSSettings,self).value(key)

        if defaultvalue is not None:
            if not value:
                self.setValue(key, defaultvalue)
                return defaultvalue

        return value

