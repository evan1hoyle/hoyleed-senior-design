import json
from treys import Card, Evaluator

def format_card_for_treys(card_str):
    rank = card_str[:-1].upper()
    suit = card_str[-1].lower()
    if rank == "10":
        rank = "T"
    return f"{rank}{suit}"

def evaluate_winner():
    evaluator = Evaluator()
    
    try:
        with open('flop_cards.json', 'r') as f:
            flop_data = json.load(f)
        with open('player_cards.json', 'r') as f:
            player_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Error: Files missing or corrupted.")
        return

    # Convert board cards, but check if flop_data is empty first
    board = [Card.new(format_card_for_treys(c['name'])) for c in flop_data.values()]
    
    # 1. Check if the board is empty
    if not board:
        print("No board cards found. Cannot evaluate.")
        return

    best_score = float('inf')
    winner_id = None
    player_results = {}

    players_dict = player_data.get('players', player_data)
    
    # 2. Check if there are actually players to evaluate
    if not players_dict:
        print("No players found in player_cards.json.")
        return

    for p_id, cards in players_dict.items():
        # Convert hand, but check if cards exist
        hand = [Card.new(format_card_for_treys(c['name'])) for c in cards.values()]
        
        # 3. Handle cases where a specific player has no cards
        if len(hand) < 2:
            player_results[p_id] = {
                "score": None,
                "hand_type": "Incomplete Hand",
                "is_winner": False
            }
            continue
        
        score = evaluator.evaluate(board, hand)
        hand_class = evaluator.get_rank_class(score)
        hand_type = evaluator.class_to_string(hand_class)
        
        player_results[p_id] = {
            "score": score,
            "hand_type": hand_type,
            "is_winner": False
        }

        if score < best_score:
            best_score = score
            winner_id = p_id

    if winner_id:
        player_results[winner_id]["is_winner"] = True

    output_data = {
        "winner_id": winner_id,
        "results": player_results
    }

    with open('winner.json', 'w') as out_file:
        json.dump(output_data, out_file, indent=4)
    
if __name__ == "__main__":
    evaluate_winner()