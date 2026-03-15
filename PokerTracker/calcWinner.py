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
        with open('PokerTracker/data/flop_cards.json', 'r') as f:
            flop_data = json.load(f)
        with open('PokerTracker/data/player_cards.json', 'r') as f:
            player_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        return

    board = [Card.new(format_card_for_treys(c['name'])) for c in flop_data.values()]
    
    if not board:
        return

    best_score = float('inf')
    winner_key = None 
    all_player_results = {}


    for client_id, players in player_data.items():
        for p_idx, cards_dict in players.items():
            
            has_down_cards = any(c['name'] == 'DN' for c in cards_dict.values())
            if has_down_cards:
                continue

            hand = [Card.new(format_card_for_treys(c['name'])) for c in cards_dict.values()]
            
            player_key = f"{client_id}_{p_idx}"
            
            if len(hand) < 2:
                all_player_results[player_key] = {
                    "client_id": client_id,
                    "player_index": p_idx,
                    "hand_type": "Incomplete Hand",
                    "is_winner": False
                }
                continue
            
            score = evaluator.evaluate(board, hand)
            hand_class = evaluator.get_rank_class(score)
            hand_type = evaluator.class_to_string(hand_class)
            
            all_player_results[player_key] = {
                "client_id": client_id,
                "player_index": p_idx,
                "score": score,
                "hand_type": hand_type,
                "is_winner": False
            }

            if score < best_score:
                best_score = score
                winner_key = player_key

    if winner_key:
        all_player_results[winner_key]["is_winner"] = True

    output_data = {
        "winner_id": winner_key,
        "results": all_player_results
    }

    with open('PokerTracker/data/winner.json', 'w') as out_file:
        json.dump(output_data, out_file, indent=4)


if __name__ == "__main__":
    evaluate_winner()