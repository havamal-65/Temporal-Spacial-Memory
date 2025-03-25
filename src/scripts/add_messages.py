from conversation_memory import ConversationMemory
import json

def main():
    try:
        # Initialize the memory system
        print("Initializing memory system...")
        memory = ConversationMemory()
        
        # Get the conversation ID
        conversations = memory.get_all_conversations()
        if not conversations:
            print("No conversations found in database")
            return
            
        conv_id = conversations[0]['id']
        print(f"Found conversation: {conv_id}")
        
        # Add the messages from The Hobbit
        messages = [
            {
                "role": "narrator",
                "content": "In a hole in the ground there lived a hobbit. Not a nasty, dirty, wet hole, filled with the ends of worms and an oozy smell, nor yet a dry, bare, sandy hole with nothing in it to sit down on or to eat: it was a hobbit-hole, and that means comfort."
            },
            {
                "role": "narrator",
                "content": "It had a perfectly round door like a porthole, painted green, with a shiny yellow brass knob in the exact middle. The door opened on to a tube-shaped hall like a tunnel: a very comfortable tunnel without smoke, with panelled walls, and floors tiled and carpeted, provided with polished chairs, and lots and lots of pegs for hats and coats -- the hobbit was fond of visitors. The tunnel wound on and on, going fairly but not quite straight into the side of the hill -- The Hill, as all the people for many miles round called it -- and many little round doors opened out of it, first on one side and then on another. No going upstairs for the hobbit: bedrooms, bathrooms, cellars, pantries (lots of these), wardrobes (he had whole rooms devoted to clothes), kitchens, dining-rooms, all were on the same floor, and indeed on the same passage. The best rooms were all on the left-hand side (going in), for these were the only ones to have windows, deep-set round windows looking over his garden, and meadows beyond, sloping down to the river."
            },
            {
                "role": "narrator",
                "content": "This hobbit was a very well-to-do hobbit, and his name was Baggins. The Bagginses had lived in the neighbourhood of The Hill for time out of mind, and people considered them very respectable, not only because most of them were rich, but also because they never had any adventures or did anything unexpected: you could tell what a Baggins would say on any question without the bother of asking him. This is a story of how a Baggins had an adventure, and found himself doing and saying things altogether unexpected. He may have lost the neighbours' respect, but he gained -- well, you will see whether he gained anything in the end."
            }
        ]
        
        # Find the conversation node
        nodes = list(memory.db.nodes.values())
        conv_node = None
        for node in nodes:
            if (node.content.get("type") == "conversation" and 
                node.content.get("id") == conv_id):
                conv_node = node
                break
                
        if not conv_node:
            print("Could not find conversation node")
            return
            
        # Add messages as nodes and connect them
        prev_node = conv_node
        for i, msg in enumerate(messages):
            # Position messages in a spiral pattern
            angle = (i * 30) % 360
            distance = 0.2 + (i * 0.05)
            
            # Create message node
            msg_node = memory.db.add_node(
                content={
                    "type": "message",
                    "conversation_id": conv_id,
                    "role": msg["role"],
                    "content": msg["content"],
                    "index": i
                },
                time=conv_node.time,
                distance=distance,
                angle=angle
            )
            
            # Connect to conversation and previous message
            memory.db.connect_nodes(conv_node.node_id, msg_node.node_id)
            if i > 0:
                memory.db.connect_nodes(prev_node.node_id, msg_node.node_id)
                
            prev_node = msg_node
            
        # Update message count
        conv_node.content["message_count"] = len(messages)
        
        # Save the database
        memory.save()
        print("Messages added successfully")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 