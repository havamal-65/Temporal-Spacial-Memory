#!/usr/bin/env python3
"""
Example script demonstrating the Mesh Tube Knowledge Database

This script creates a sample knowledge database modeling a conversation
about AI, machine learning, and related concepts, showing how topics
evolve and connect over time.
"""

import os
import random
from datetime import datetime

# Use absolute imports
from src.models.mesh_tube import MeshTube
from src.utils.position_calculator import PositionCalculator
from src.visualization.mesh_visualizer import MeshVisualizer

def create_sample_database():
    """Create a sample mesh tube database with AI-related topics"""
    # Create a new mesh tube instance
    mesh = MeshTube(name="AI Conversation", storage_path="data")
    
    print(f"Created new Mesh Tube: {mesh.name}")
    
    # Add some initial core topics (at time 0)
    ai_node = mesh.add_node(
        content={"topic": "Artificial Intelligence", "description": "The field of AI research"},
        time=0,
        distance=0.1,  # Close to center (core topic)
        angle=0
    )
    
    ml_node = mesh.add_node(
        content={"topic": "Machine Learning", "description": "A subfield of AI focused on learning from data"},
        time=0,
        distance=0.3,
        angle=45
    )
    
    dl_node = mesh.add_node(
        content={"topic": "Deep Learning", "description": "A subfield of ML using neural networks"},
        time=0,
        distance=0.5,
        angle=90
    )
    
    # Connect related topics
    mesh.connect_nodes(ai_node.node_id, ml_node.node_id)
    mesh.connect_nodes(ml_node.node_id, dl_node.node_id)
    
    # Add some specific AI models (at time 1)
    gpt_node = mesh.add_node(
        content={"topic": "GPT Models", "description": "Large language models by OpenAI"},
        time=1,
        distance=0.7,
        angle=30
    )
    
    bert_node = mesh.add_node(
        content={"topic": "BERT", "description": "Bidirectional Encoder Representations from Transformers"},
        time=1,
        distance=0.8,
        angle=60
    )
    
    # Connect models to related topics
    mesh.connect_nodes(ml_node.node_id, gpt_node.node_id)
    mesh.connect_nodes(dl_node.node_id, gpt_node.node_id)
    mesh.connect_nodes(dl_node.node_id, bert_node.node_id)
    mesh.connect_nodes(gpt_node.node_id, bert_node.node_id)
    
    # Add applications of AI (at time 2)
    nlp_node = mesh.add_node(
        content={"topic": "Natural Language Processing", "description": "AI for understanding language"},
        time=2,
        distance=0.4,
        angle=15
    )
    
    cv_node = mesh.add_node(
        content={"topic": "Computer Vision", "description": "AI for understanding images"},
        time=2,
        distance=0.5,
        angle=180
    )
    
    # Connect applications to related areas
    mesh.connect_nodes(ai_node.node_id, nlp_node.node_id)
    mesh.connect_nodes(ml_node.node_id, nlp_node.node_id)
    mesh.connect_nodes(gpt_node.node_id, nlp_node.node_id)
    mesh.connect_nodes(ai_node.node_id, cv_node.node_id)
    mesh.connect_nodes(ml_node.node_id, cv_node.node_id)
    
    # Create some deltas (updates to existing topics over time)
    
    # Update to GPT at time 3
    gpt_update = mesh.apply_delta(
        original_node=gpt_node,
        delta_content={"versions": ["GPT-3", "GPT-3.5", "GPT-4"], "capabilities": "Advanced reasoning"},
        time=3
    )
    
    # Update to NLP at time 3.5
    nlp_update = mesh.apply_delta(
        original_node=nlp_node,
        delta_content={"applications": ["Translation", "Summarization", "Question Answering"]},
        time=3.5
    )
    
    # Add new topics at time 4
    ethics_node = mesh.add_node(
        content={"topic": "AI Ethics", "description": "Ethical considerations in AI development and use"},
        time=4,
        distance=0.3,
        angle=270
    )
    
    # Use the position calculator to place a new node
    # based on its relationships to existing nodes
    time, distance, angle = PositionCalculator.suggest_position_for_new_topic(
        mesh_tube=mesh,
        content={"topic": "Prompt Engineering", "description": "Designing effective prompts for LLMs"},
        related_node_ids=[gpt_node.node_id, nlp_node.node_id],
        current_time=4.5
    )
    
    prompt_eng_node = mesh.add_node(
        content={"topic": "Prompt Engineering", "description": "Designing effective prompts for LLMs"},
        time=time,
        distance=distance,
        angle=angle
    )
    
    # Connect new topics
    mesh.connect_nodes(ai_node.node_id, ethics_node.node_id)
    mesh.connect_nodes(gpt_update.node_id, prompt_eng_node.node_id)
    mesh.connect_nodes(nlp_update.node_id, prompt_eng_node.node_id)
    
    # Add more topics at time 5 using position calculator
    for topic, desc, related_ids in [
        ("Reinforcement Learning", "Learning through rewards and penalties", [ml_node.node_id, ai_node.node_id]),
        ("Transformers", "Neural network architecture", [dl_node.node_id, gpt_node.node_id, bert_node.node_id]),
        ("RAG", "Retrieval Augmented Generation", [gpt_update.node_id, prompt_eng_node.node_id]),
        ("Fine-tuning", "Adapting pre-trained models", [gpt_update.node_id, bert_node.node_id, ml_node.node_id]),
        ("Hallucinations", "AI generating false information", [ethics_node.node_id, gpt_update.node_id])
    ]:
        time, distance, angle = PositionCalculator.suggest_position_for_new_topic(
            mesh_tube=mesh,
            content={"topic": topic, "description": desc},
            related_node_ids=related_ids,
            current_time=5
        )
        
        new_node = mesh.add_node(
            content={"topic": topic, "description": desc},
            time=time,
            distance=distance,
            angle=angle
        )
        
        # Connect to related nodes
        for rel_id in related_ids:
            mesh.connect_nodes(new_node.node_id, rel_id)
    
    # Save the database
    os.makedirs("data", exist_ok=True)
    mesh.save(filepath="data/ai_conversation.json")
    
    return mesh

def explore_database(mesh):
    """Demonstrate various ways to explore and visualize the database"""
    # Print overall statistics
    print("\n" + "=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)
    print(MeshVisualizer.print_mesh_stats(mesh))
    
    # Visualize timeline
    print("\n" + "=" * 50)
    print("TIMELINE VISUALIZATION")
    print("=" * 50)
    print(MeshVisualizer.visualize_timeline(mesh))
    
    # Visualize temporal slices
    for time in [0, 2, 5]:
        print("\n" + "=" * 50)
        print(f"TEMPORAL SLICE AT TIME {time}")
        print("=" * 50)
        print(MeshVisualizer.visualize_temporal_slice(mesh, time, tolerance=0.5, show_ids=True))
    
    # Find a node about GPT models
    gpt_nodes = [node for node in mesh.nodes.values() 
                if "GPT" in str(node.content)]
    
    if gpt_nodes:
        gpt_node = gpt_nodes[0]
        
        # Visualize connections
        print("\n" + "=" * 50)
        print(f"CONNECTIONS FOR GPT NODE")
        print("=" * 50)
        print(MeshVisualizer.visualize_connections(mesh, gpt_node.node_id))
        
        # Compute full state of the node (with deltas applied)
        print("\n" + "=" * 50)
        print(f"COMPUTED STATE FOR GPT NODE")
        print("=" * 50)
        full_state = mesh.compute_node_state(gpt_node.node_id)
        for key, value in full_state.items():
            print(f"{key}: {value}")
            
        # Find nearest nodes
        print("\n" + "=" * 50)
        print(f"NEAREST NODES TO GPT NODE")
        print("=" * 50)
        nearest = mesh.get_nearest_nodes(gpt_node, limit=5)
        for i, (node, distance) in enumerate(nearest):
            print(f"{i+1}. {node.content.get('topic', 'Unknown')} - Distance: {distance:.2f}")
            
        # Predict topic probability
        print("\n" + "=" * 50)
        print(f"PROBABILITY PREDICTIONS FOR FUTURE MENTIONS")
        print("=" * 50)
        
        # Predict probabilities for a few nodes at future time 7
        for node in list(mesh.nodes.values())[:5]:
            topic = node.content.get('topic', 'Unknown')
            prob = mesh.predict_topic_probability(node.node_id, future_time=7)
            print(f"Topic '{topic}' at time 7: {prob:.2%} probability")

def demo_delta_encoding(mesh):
    """Demonstrate delta encoding functionality"""
    print("\n" + "=" * 50)
    print("DELTA ENCODING DEMONSTRATION")
    print("=" * 50)
    
    # Find ethics node
    ethics_nodes = [node for node in mesh.nodes.values() 
                   if node.content.get('topic') == "AI Ethics"]
    
    if not ethics_nodes:
        print("Ethics node not found")
        return
        
    ethics_node = ethics_nodes[0]
    print(f"Original Ethics Node Content: {ethics_node.content}")
    
    # Create a series of delta updates
    deltas = [
        {"concerns": ["Bias", "Privacy"]},
        {"concerns": ["Bias", "Privacy", "Job Displacement"], "regulations": ["EU AI Act"]},
        {"concerns": ["Bias", "Privacy", "Job Displacement", "Existential Risk"], 
         "regulations": ["EU AI Act", "US Executive Order"]}
    ]
    
    # Apply deltas at incrementing times
    last_node = ethics_node
    for i, delta in enumerate(deltas):
        last_node = mesh.apply_delta(
            original_node=last_node,
            delta_content=delta,
            time=ethics_node.time + i + 1
        )
        print(f"\nDelta {i+1} at time {last_node.time}: {delta}")
    
    # Compute the full state
    full_state = mesh.compute_node_state(last_node.node_id)
    print("\nFull computed state of Ethics topic after all deltas:")
    for key, value in full_state.items():
        print(f"{key}: {value}")

def main():
    print("Mesh Tube Knowledge Database Example")
    print("===================================")
    
    # Create or load database
    if os.path.exists("data/ai_conversation.json"):
        print("Loading existing database...")
        mesh = MeshTube.load("data/ai_conversation.json")
    else:
        print("Creating new sample database...")
        mesh = create_sample_database()
    
    # Explore the database
    explore_database(mesh)
    
    # Demonstrate delta encoding
    demo_delta_encoding(mesh)
    
    print("\nExample completed!")

if __name__ == "__main__":
    main() 