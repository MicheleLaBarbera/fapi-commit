from typing import Annotated

from fastapi import Header, HTTPException

import networkx as nx
import random
import math 

class ConceptMap():
	color_entropy: int
	color_entropy_percent: int
	color_effort: int
	nodes_count: int 
	edges_count: int 
	entropy: float 
	entropy_percent: float
	effort: float

	graph: nx.DiGraph

	def __init__(self):
		self.graph = nx.null_graph()
		self.adjacency_matrix = None
		self.entropy = 0
		self.entropy_percent = 0
		self.effort = 0
		self.ordered_nodes = []
	
	def generate(self, node_min: int, node_max: int) -> bool:
		if node_min > node_max: # Check if minimum nodes is above than its maximum
			return False

		nodes_count = random.randint(node_min, node_max) # Generate a number between the minimum and the maximum of nodes count

		self.graph = nx.random_tree(nodes_count, create_using=nx.DiGraph)
		self.ordered_nodes = list(nx.topological_sort(self.graph))

		extra_edges_count = random.randint(0, nodes_count * 2 - 5)

		for _ in range(extra_edges_count):
			random_first_node_idx = random.randint(0, len(self.ordered_nodes) - 1)
			random_first_node = self.ordered_nodes[random_first_node_idx]
						
			if random_first_node_idx + 1 < len(self.ordered_nodes) - 1:
				random_second_node = self.ordered_nodes[random.randint(random_first_node_idx + 1, len(self.ordered_nodes) - 1)]

				self.graph.add_edge(random_first_node, random_second_node)
				self.ordered_nodes = list(nx.topological_sort(self.graph))


		# Convert the generated directed acyclic graph (DAG) to an adjacency matrix
		self.adjacency_matrix = nx.adjacency_matrix(self.graph).todense()

		# Entropy calculation
		self.calculate_entropy()
		return True
	
	def set_entropy_percent(self, value): 
		if(value >= 0 and value <= 100):
			self.entropy_percent = value

	def get_entropy_percent(self):
		return self.entropy_percent

	def get_adjacency_matrix(self):
		return self.adjacency_matrix

	def get_nodes_count(self) -> int:
		return self.graph.number_of_nodes()

	def get_edges_count(self) -> int:
		return self.graph.number_of_edges()

	def get_entropy(self) -> int:
		return self.entropy

	def get_effort(self) -> int:
		return self.effort 

	def calculate_entropy(self) -> int:
		entropy_max = [0, 0, 0, 1,2.584962501,4.584962501,6.906890596,9.491853096,12.29920802,15.29920802,18.46913302,21.79106111,25.25049273,28.83545523,32.53589495,36.34324987,40.25014047,44.25014047,48.33760331,52.50752831,56.75545583,61.07738392,65.46970134,69.92913296,74.45269492,79.03765742,83.68151361,88.38195333,93.13684083,97.94419575,102.8021767]
		for x in self.adjacency_matrix:
			links_count = 0 
			for y in x: # Check for every node how many links it has
				if y == 1:
					links_count = links_count + 1
			
			node_entropy = 0
			if links_count > 0:
				probability = 1 / links_count 
				for _ in range(links_count):
					node_entropy = node_entropy + abs((probability * math.log(probability, 2))) # Entropy formula

			self.entropy = self.entropy + node_entropy

		if self.get_nodes_count() >= 0 and self.get_nodes_count() <= 30:
			self.entropy_percent = (self.entropy / entropy_max[self.get_nodes_count()]) * 100

			self.effort = (self.entropy_percent / 100) * self.get_nodes_count() * self.get_edges_count()

	
		
		