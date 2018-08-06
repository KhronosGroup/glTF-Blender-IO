import logging

class Log():
    def __init__(self, loglevel):
        self.logger = logging.getLogger('glTFImporter')
        self.hdlr = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        self.hdlr.setFormatter(formatter)
        self.logger.addHandler(self.hdlr)
        self.logger.setLevel(int(loglevel))

    def getLevels():
        levels = [
        (str(logging.CRITICAL), "Critical", "", logging.CRITICAL),
        (str(logging.ERROR), "Error", "", logging.ERROR),
        (str(logging.WARNING), "Warning", "", logging.WARNING),
        (str(logging.INFO), "Info", "", logging.INFO),
        (str(logging.NOTSET), "NotSet", "", logging.NOTSET)
        ]

        return levels

    def default():
        return str(logging.ERROR)
