class Color:
    WHITE = (255, 255, 255)
    BLACK = (255, 255, 255)

class T_Color:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
def log(msg):
    msg = msg.replace("(/)", T_Color.RESET)
    msg = msg.replace("(C)", T_Color.CYAN)
    msg = msg.replace("(P)", T_Color.PURPLE)
    print(msg)