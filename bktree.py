
def levenshtein(s1, s2):
    """ https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python """
    if len(s1) < len(s2): return levenshtein(s2, s1)
    if len(s2) == 0: return len(s1)
    if (s1 == s2): return 0
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

# Xenopax implementation ported to Python
class BKTree:
    def __init__(self):
        self.root = None

    def add(self, word):
        word = word.lower()
        if self.root is None:
            self.root = Node(word)
            return

        cur_node = self.root
        dist = levenshtein(cur_node.word, word)
        while cur_node.contains_key(dist):
            if dist == 0: return
            cur_node = cur_node[dist]
            dist = levenshtein(cur_node.word, word)
        
        cur_node.add_child(dist, word)

    def search(self, word, d=2):
        word = word.lower()
        candidates = []
        self.recursive_search(self.root, candidates, word, d)
        return candidates

        # if search needs to guarantee a result
        # if len(candidates) == 0: return self.search(word, d+1)

    def recursive_search(self, node, candidates, word, d):
        """ returns True to terminate search """
        cur_dist = levenshtein(node.word, word)
        min_dist = cur_dist - d
        max_dist = cur_dist + d

        if cur_dist == 0:
            candidates.clear()
            candidates.append(word)
            return True # early termination
        if (cur_dist <= d):
            candidates.append(node.word)
        for key in node.keys():
            if min_dist <= key <= max_dist:
                terminate = self.recursive_search(node[key], candidates, word, d)
                if terminate: return terminate
class Node:
    def __init__(self, word):
        self.word = word.lower()
        self.children = {}

    def __getitem__(self, index):
        return self.children[index]

    def keys(self):
        return list(self.children.keys())

    def contains_key(self, key):
        return key in self.children

    def add_child(self, key, word):
        self.children[key] = Node(word)

def build(search_space):
    tree = BKTree()
    for word in search_space:
        tree.add(word)
    return tree

    

    
