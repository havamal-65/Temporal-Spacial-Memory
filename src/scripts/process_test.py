import process_tolkien

text_sample = """AN UNEXPECTED PARTY
IN A HOLE IN THE GROUND there lived a hobbit. Not a nasty, dirty, wet
hole, filled with the ends of worms and an oozy smell, nor yet a dry,
bare, sandy hole with nothing in it to sit down on or to eat: it was
a hobbit-hole, and that means comfort."""

result_id = process_tolkien.process_direct_text(text_sample)
print(f"Processed text with ID: {result_id}") 