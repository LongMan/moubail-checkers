import copy, pprint, random, logging, pprint
from datetime import datetime, timedelta

from appengine_django.models import BaseModel
from google.appengine.ext import db

from django.utils import simplejson as sj

class Player(db.Expando):
    imei = db.StringProperty()
    score = db.IntegerProperty()
    game = db.ReferenceProperty()
    
    created_at = db.DateTimeProperty(auto_now_add=True)
    game_requested = db.DateTimeProperty()
    alive_at = db.DateTimeProperty(auto_now=True)
    
    #def game(self):
    #    return self.checkersgames1.get() or self.checkersgames2.get()


class Checker:
    def __init__(self, player, ctype="Normal"):
        self.player = player
        self.ctype = ctype
        
    def is_king(self):
        return self.ctype == "King"
        
    def make_king(self):
        self.ctype = "King"
    
    def dump_to_list(self):
        return [self.player.key(), self.ctype]

class Board:
    """ 
    8x8 checkers board. Player1 it on top, Player2 on the bottom.
    +---------------+
    |1   1   1   1  |
    |  1       1   1|
    |1   1   1   1  |
    |               |
    |               |
    |  2   2   2   2|
    |2   2   2   2  |
    |  2   2   2   2|
    +---------------+
    Coordinates:
        - left upper:   [0][0]
        - right upper:  [7][0]
        - left bottom:  [0][7]
        - right bottom: [7][7]
     
    Acessing cells by self.checkers[2][1]
    """
    
    empty = [[None for i in range(8)] for i in range(8)]
    PLAYER1_MOVES = [[+1, +1], [-1, +1]]
    PLAYER2_MOVES = [[+1, -1], [-1, -1]]
    KING_MOVES = PLAYER1_MOVES + PLAYER2_MOVES 
    def __init__(self, player1, player2, board_list=[],):
        self.player1 = player1
        self.player2 = player2
        if not board_list:
            self.checkers = self.start_configuration(player1, player2)
            return
        self.checkers = copy.deepcopy(Board.empty)
        for x in range(len(board_list)):
            for y in range(len(board_list[x])):
                for player in [player1, player2]:
                    if board_list[x][y] and player.key().__str__() == board_list[x][y][0]:
                        self.checkers[x][y] = Checker(player, board_list[x][y][1])
                        
    def player_checkers_coords(self, player):
        player_checkers_coords = []
        for x in range(len(self.checkers)):
            for y in range(len(self.checkers[x])):
                if self.checkers[x][y] and self.checkers[x][y].player.key() == player.key():
                    player_checkers_coords.append([x,y])
                    
        return player_checkers_coords
        
    def reinit_from_test_board(self, t_board):
        t_board = [[s for s in line] for line in t_board]
        for x in range(len(t_board)):
            for y in range(len(t_board[x])):
                cell = t_board[x][y]
                if cell == " ":
                    self.checkers[y][x] = None
                else:
                    if cell in ['F', 'S']: ctype = "King"
                    else: ctype = "Normal"
                    if cell in ['f', 'F']: player = self.player1
                    else: player = self.player2
                    self.checkers[y][x] = Checker(player, ctype)
                        
    def dump_to_list(self):
        dump = copy.deepcopy(self.checkers)
        for x in range(len(dump)):
            for y in range(len(dump[x])):
                try:
                    dump[x][y] = [dump[x][y].player.key().__str__(), dump[x][y].ctype] 
                except AttributeError:
                    pass
        return dump                
    
    def start_configuration(self, player1, player2):
        checkers = copy.deepcopy(Board.empty)
        for x in range(len(checkers)):
            for y in range(len(checkers[x])):
                if y in [0,1,2] and (x+y)%2 == 0:
                    checkers[x][y] = Checker(player1)
                elif y in [5,6,7] and (x+y)%2 == 0:
                    checkers[x][y] = Checker(player2)
        return checkers
    
    def pretty_print(self):
        print
        for y in range(len(self.checkers[0])):
            for x in range(len(self.checkers)):
                if self.checkers[x][y] == None:
                    print " ",
                else:
                    print self.player_to_number(self.checkers[x][y].player),
            print
    
    def player_to_number(self, player):
        number = None
        if player.key() == self.player1.key(): number = 1
        elif  player.key() == self.player2.key(): number = 2
        return number
        
    def update_checker_kingity(self, coords):
        checker = self.checkers[coords[0]][coords[1]]
        if (coords[1] == (len(self.checkers[0]) - 1) and checker.player.key() == self.player1.key()) or \
           (coords[1] == 0 and checker.player.key() == self.player2.key()):
           checker.make_king()
        
    
    def move(self, fr, to):
        checker = self.checkers[fr[0]][fr[1]]
        if not checker: return []
        moves = self.possible_moves_for_player(checker.player)

        for move in moves:
            if [fr, to] == move[:2]:
                logging.warn("Moving %s from %s to %s"%(checker, fr, to))
                if move[2]:
                    eaten = move[2]
                    logging.info("Eating %s"%move[2])
                    self.checkers[eaten[0]][eaten[1]] = None 
                self.checkers[fr[0]][fr[1]] = None
                self.checkers[to[0]][to[1]] = checker
                self.update_checker_kingity(to)
                break
                
    def possible_moves_for_player(self, player):
        moves = []
        for x in range(len(self.checkers)):
            for y in range(len(self.checkers[x])):
                checker = self.checkers[x][y]
                
                if not checker or checker.player.key() != player.key(): continue
                
                moves += self.possible_moves_for_checker([x,y])
        
        # Disabled to sync with js version
        #eaten_moves = filter(lambda x: x[2] != None, moves)
        #if len(eaten_moves) > 0:
        #    return eaten_moves
        
        return moves      
                
                
                
    def cell(self, coords):
        return 0 <= coords[0] < len(self.checkers) and \
               0 <= coords[1] < len(self.checkers[0]) and \
               self.checkers[coords[0]][coords[1]]
        
    def possible_moves_for_checker(self, coords):
        checker = self.checkers[coords[0]][coords[1]]
        if not checker: return None
        moves = []
        owner = checker.player
        ctype = checker.ctype
        
        # Getting standard moves for this checker
        # Standart move is diagonal move without eating an opponent checker
        if ctype == "King": standard_moves = Board.KING_MOVES
        elif owner.key() == self.player1.key(): standard_moves = Board.PLAYER1_MOVES
        elif owner.key() == self.player2.key(): standard_moves = Board.PLAYER2_MOVES
        
        
        for s_move in standard_moves:
            new_coords = map(lambda x,y: x + y, coords, s_move)
            
            new_cell = self.cell(new_coords)

            if new_cell == False: continue
            
            # If peaceful move is acceptable - adding it to possible moves
            if new_cell == None: 
                moves.append([coords, new_coords, None])
                continue   
            
            # In other case we've got a preventer
            preventer = new_cell
            
            # If its a turner's cheker - calm down
            if preventer.player.key() == owner.key(): continue

            eating_coords = map(lambda x,y: x + y, new_coords, s_move) 
            
            new_cell = self.cell(eating_coords)
            
            if new_cell == False: continue
            if new_cell == None: moves.append([coords, eating_coords, new_coords])

        return moves
                
            
                
            

    def __call__(self, x, y):
        return self.checkers[x][y]
    
class CheckersGame(db.Model):
    player1 = db.ReferenceProperty(Player, collection_name="checkersgames1")
    player2 = db.ReferenceProperty(Player, collection_name="checkersgames2")
    winner = db.ReferenceProperty(Player, collection_name="checkersgames_winner")
    
    state = db.TextProperty()
    turner = db.ReferenceProperty(Player, collection_name="checkersgames_turner")
    is_over = db.BooleanProperty(default=False)
    
    created_at = db.DateTimeProperty(auto_now_add=True)
    last_update_at = db.DateTimeProperty(auto_now=True)
    last_turn_at = db.DateTimeProperty()
    timeout = db.IntegerProperty()

    TURN_TIME = timedelta(0, 120)

    @classmethod
    def create(cls, *a, **k):
        game = CheckersGame(*a, **k)
        game.put()
        game.player1.game = game
        game.player2.game = game
        return game        
        
    def player_to_number(self, player):
        return ((player.key() == self.player1.key()) and 1) or 2
    
    def get_waiter(self):
        if self.turner.key() == self.player1.key(): return self.player2
        return self.player1
    
    def for_player1(self):
        return self.requester and self.requester.key() == self.player1.key()
    
    def for_player2(self):
        return self.requester and self.requester.key() == self.player2.key()
        
    def check_over(self):
        if self.is_over: return True
        
        if not self.board.player_checkers_coords(self.player2):
            logging.info("no checkers for player 2")
            self.winner = self.player1
        elif not self.board.player_checkers_coords(self.player1):
            logging.info("no checkers for player 1")
            self.winner = self.player2
        elif not self.board.possible_moves_for_player(self.turner):
            logging.info("no checkers for turner (player %s)"%self.player_to_number(self.turner))
            self.winner = self.get_waiter()
        elif (datetime.now() - self.turner.alive_at) > CheckersGame.TURN_TIME:
            logging.info("gameover on timeout by player %s"%self.player_to_number(self.turner))            
            self.winner = self.get_waiter()
                        
        self.is_over = bool(self.winner)        
        return self.is_over
        
    def requester_is_turner(self):
        logging.info("requester is turner " + str(self.requester.key() == self.turner.key()))
        return self.requester.key() == self.turner.key()
        
    def requester_is_winner(self):
        if not self.winner: return False
        return self.winner.key() == self.requester.key()

    def change_turner(self):
        if self.turner.key() == self.player1.key():
            self.turner = self.player2
        else:
            self.turner = self.player1
    
    def player_coords(self, xy):
        if self.for_player1(): return [int(xy[1]), int(xy[0])]
        elif self.for_player2(): return [7-int(xy[1]), 7-int(xy[0])]
    
    def setup(self, player=None):
        if self.state:
            self.unpack()
        else:
            self.board = Board(self.player1, self.player2)
            self.turner = random.choice([self.player1, self.player2])
        self.requester = player
    
    def pack(self):
        dump = self.board.dump_to_list()   
        self.state = sj.dumps({'board' : dump})
        logging.info("Game packed")
    
    def save(self):
        self.pack()
        self.put()
        logging.info("Game saved")
    
    def unpack(self):
        self.board = Board(self.player1, self.player2, sj.loads(self.state)["board"])    
    
    def apply_turn_queue(self, turnqueue):
        logging.info("get queue %s"%turnqueue)
        if not self.requester_is_turner() or self.is_over: return False            
        logging.info("this queue is accepable")
        while turnqueue:
            turn = turnqueue[:4]
            turnqueue = turnqueue[4:]
            self.board.move(self.player_coords(turn[2:]), self.player_coords(turn[:2]))
        self.last_turn_at = datetime.now()
        self.change_turner()

    def to_response(self):
        response_board = self.board.dump_to_list()
        if self.for_player2(): 
            response_board = copy.deepcopy(response_board)
            response_board.reverse()
            for i in range(len(response_board)):
                response_board[i].reverse()
        for x in range(len(response_board)):
            for y in range(len(response_board[x])):
                if not response_board[x][y]:
                    response_board[x][y] = False
                elif response_board[x][y][0] == self.requester.key().__str__():
                    response_board[x][y] = "1%s"%response_board[x][y][1][0]
                else:
                    response_board[x][y] = "2%s"%response_board[x][y][1][0]
        return {'board': response_board, 'your_turn': self.requester_is_turner(), 'status': self.status(), 
                'you_win': self.requester_is_winner()}

    def status(self):
        if self.is_over : return 'over'
        return 'onair'
        
        
    
