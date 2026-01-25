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
    except FileNotFoundError:
        print("Waiting for JSON files...")
        return

    board = [Card.new(format_card_for_treys(c['name'])) for c in flop_data.values()]
    
    best_score = float('inf')
    winner_id = None
    player_results = {}

    players_dict = player_data.get('players', player_data)
    
    # First pass: Calculate scores
    for p_id, cards in players_dict.items():
        hand = [Card.new(format_card_for_treys(c['name'])) for c in cards.values()]
        
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

    # Mark the winner
    if winner_id:
        player_results[winner_id]["is_winner"] = True

    # Prepare final output object
    output_data = {
        "winner_id": winner_id,
        "results": player_results
    }

    # Write to JSON file
    with open('winner.json', 'w') as out_file:
        json.dump(output_data, out_file, indent=4)
    
if __name__ == "__main__":
    evaluate_winner()