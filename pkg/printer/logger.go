package printer

import "github.com/sirupsen/logrus"

// Log prints logs if necessary.
func Log(logger *logrus.Logger, level logrus.Level, strict bool, format string, args ...interface{}) {
	if logger != nil && logger.Level >= level {
		if strict && logger.Level != level {
			return
		}
		switch level {
		case logrus.DebugLevel:
			logger.Debugf(format, args)
		case logrus.InfoLevel:
			logger.Infof(format, args)
		case logrus.WarnLevel:
			logger.Warnf(format, args)
		case logrus.ErrorLevel:
			logger.Errorf(format, args)
		case logrus.FatalLevel:
			logger.Fatalf(format, args)
		default:
			logger.Panicf(format, args)
		}
	}
}
