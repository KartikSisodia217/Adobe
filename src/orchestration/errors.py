class AimlessError(Exception):
    pass

class FatalValidation(AimlessError):
    pass

class RecoverableError(AimlessError):
    pass
