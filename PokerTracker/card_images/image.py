from PIL import Image
import os

# --- Configuration ---
background_file = 'back.png'

# List of all card files from your original prompt (excluding 'back.png' and 'jokers' for now)
# You should verify this list is 100% accurate for your files.
card_files = [
    '10_of_clubs.png', '10_of_diamonds.png', '10_of_hearts.png', '10_of_spades.png',
    '2_of_clubs.png', '2_of_diamonds.png', '2_of_hearts.png', '2_of_spades.png',
    '3_of_clubs.png', '3_of_diamonds.png', '3_of_hearts.png', '3_of_spades.png',
    '4_of_clubs.png', '4_of_diamonds.png', '4_of_hearts.png', '4_of_spades.png',
    '5_of_clubs.png', '5_of_diamonds.png', '5_of_hearts.png', '5_of_spades.png',
    '6_of_clubs.png', '6_of_diamonds.png', '6_of_hearts.png', '6_of_spades.png',
    '7_of_clubs.png', '7_of_diamonds.png', '7_of_hearts.png', '7_of_spades.png',
    '8_of_clubs.png', '8_of_diamonds.png', '8_of_hearts.png', '8_of_spades.png',
    '9_of_clubs.png', '9_of_diamonds.png', '9_of_hearts.png', '9_of_spades.png',
    'ace_of_clubs.png', 'ace_of_diamonds.png', 'ace_of_hearts.png', 'ace_of_spades.png',
    'jack_of_clubs.png', 'jack_of_diamonds.png', 'jack_of_hearts.png', 'jack_of_spades.png',
    'king_of_clubs.png', 'king_of_diamonds.png', 'king_of_hearts.png', 'king_of_spades.png',
    'queen_of_clubs.png', 'queen_of_diamonds.png', 'queen_of_hearts.png', 'queen_of_spades.png',
    # Include Jokers if you want them processed too
    'black_joker.png', 'red_joker.png'
]
# --- End Configuration ---


try:
    # Load the background once outside the loop
    background_template = Image.open(background_file)
    
    print(f"Starting batch process on {len(card_files)} card images...")

    for card_file in card_files:
        # Check if the file exists before processing
        if not os.path.exists(card_file):
            print(f"Skipping: {card_file} not found.")
            continue

        try:
            # 1. Open the card image
            card = Image.open(card_file)

            # 2. Ensure the card has an alpha channel
            if card.mode != 'RGBA':
                card = card.convert('RGBA')

            # Get card dimensions
            card_width, card_height = card.size

            # 3. Resize the background copy to match the card's dimensions
            # Using the old constant Image.LANCZOS for compatibility
            resized_background = background_template.resize(
                (card_width, card_height), 
                Image.LANCZOS
            )

            # 4. Paste the card onto the resized background
            final_image = resized_background.copy()
            final_image.paste(card, (0, 0), mask=card)

            # 5. Save the resulting image, overwriting the original file name
            final_image.save(card_file)
            
            print(f"Processed and saved: {card_file}")

        except Exception as e:
            print(f"Failed to process {card_file}: {e}")

    print("\nBatch processing complete.")

except FileNotFoundError:
    print(f"Critical Error: The background file '{background_file}' was not found.")
except Exception as e:
    print(f"A general error occurred: {e}")