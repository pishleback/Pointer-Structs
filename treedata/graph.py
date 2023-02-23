from treedata import data
import math



class Graph():
    def __init__(self, tree : data.Tree):
        assert type(tree) == data.Tree

        self.tree = tree

        self.nodes = [] #idents of people and partnerships
        self.adj_up = {} #ident -> [idents of upwards people and partnerships]
        self.adj_down = {} #ident -> [idents of downwards people and partnerships]

        for ident, entity in tree.entity_lookup.items():
            if type(entity) in [data.Person, data.Partnership]:
                self.nodes.append(ident)
                self.adj_up[ident] = []
                self.adj_down[ident] = []

                if type(entity) == data.Partnership:
                    for parent_ptr in entity.parents:
                        self.adj_up[ident].append(parent_ptr.to_entity.ident)
                        self.adj_down[parent_ptr.to_entity.ident].append(ident)
                    for child_ptr in entity.children:
                        self.adj_down[ident].append(child_ptr.to_entity.ident)
                        self.adj_up[child_ptr.to_entity.ident].append(ident)
            
        for ident in self.nodes:
            assert ident in self.adj_up
            for up_ident in self.adj_up[ident]:
                assert ident in self.adj_down[up_ident]

        for ident in self.nodes:
            assert ident in self.adj_down
            for down_ident in self.adj_down[ident]:
                assert ident in self.adj_up[down_ident]

    def pos_info(self, root):
        assert root in self.nodes

        tree_adj_up = {ident : [] for ident in self.nodes}
        tree_adj_down = {ident : [] for ident in self.nodes}
        tree_heights = {root : 0}
        found = set([root])
        boundary = set([root])

        #do a breadth first tree generation to get heights & tree adjacency info
        new_boundary = set()
        while len(boundary) > 0:
            new_boundary = set()
            for boundary_ident in boundary:
                for up_ident in self.adj_up[boundary_ident]:
                    if not up_ident in found:
                        found.add(up_ident)
                        new_boundary.add(up_ident)
                        tree_heights[up_ident] = tree_heights[boundary_ident] + 1
                        tree_adj_up[boundary_ident].append(up_ident)
                        tree_adj_down[up_ident].append(boundary_ident)

                for down_ident in self.adj_down[boundary_ident]:
                    if not down_ident in found:
                        found.add(down_ident)
                        new_boundary.add(down_ident)
                        tree_heights[down_ident] = tree_heights[boundary_ident] - 1
                        tree_adj_down[boundary_ident].append(down_ident)
                        tree_adj_up[down_ident].append(boundary_ident)

            boundary = new_boundary

        def eval_order(ident):
            return ident

        def stack_left(new, existing):
            existing_hs = set(tree_heights[ident] for ident in existing)
            new_hs = set(tree_heights[ident] for ident in new)
            common_hs = existing_hs & new_hs
            assert len(common_hs) != 0
            off = min(min(existing[ident] for ident in existing if tree_heights[ident] == h) - max(new[ident] for ident in new if tree_heights[ident] == h) for h in common_hs)
            ans = {ident : x for ident, x in existing.items()}
            for ident, x in new.items():
                ans[ident] = new[ident] + off - 1
            return ans

        def stack_right(existing, new):
            existing_hs = set(tree_heights[ident] for ident in existing)
            new_hs = set(tree_heights[ident] for ident in new)
            common_hs = existing_hs & new_hs
            assert len(common_hs) != 0
            off = min(min(new[ident] for ident in new if tree_heights[ident] == h) - max(existing[ident] for ident in existing if tree_heights[ident] == h) for h in common_hs)
            ans = {ident : x for ident, x in existing.items()}
            for ident, x in new.items():
                ans[ident] = new[ident] - off + 1
            return ans
        
        def stack_together(parts):
            if len(parts) == 0:
                return {}
            elif len(parts) == 1:
                return parts[0]
            else:
                ans = parts[0]
                for other_part in parts[1:]:
                    ans = stack_right(ans, other_part)
                #TODO: make this betterer by doing some fancy averaging to put stuff in the middle of where it can go
                return ans

        
        #compute positions () using sus algorithm
        def generate_pos_down(base, depth):
            if depth == 0:
                return {base : 0.0}
            
            pos_downs = [generate_pos_down(base_down, depth - 1) for base_down in sorted(tree_adj_down[base], key = eval_order)]
            if len(pos_downs) == 0:
                ans = {base : 0}
            else:
                ans = stack_together(pos_downs)
                down_poses = [ans[base_down] for base_down in sorted(tree_adj_down[base], key = eval_order)]
                d_min = min(down_poses)
                d_max = max(down_poses)
                off = 0.5 * (d_min + d_max)
                ans = {ident : ans[ident] - off for ident in ans}
                ans[base] = 0.0

            #add partners
            if type(self.tree.entity_lookup[base]) == data.Person:
                if len(tree_adj_down[base]) == 1: #if they have exactly one partner (i may handle other cases too at some point? especially 2 partners as one can go each side in that case)
                    part_ident = tree_adj_down[base][0]
                    if len(tree_adj_up[part_ident]) == 2: #if there are exactly two parents. other possible cases are 1 parent (base) or more than 2 (which is too weird to bother handling here)
                        parent_1, parent_2 = tree_adj_up[part_ident]
                        if base == parent_1:
                            partner = parent_2
                        else:
                            assert base == parent_2
                            partner = parent_1
                        if eval_order(partner) < eval_order(base):
                            ans[base] = 0.5
                            ans[partner] = ans[base] - 1
                        else:
                            ans[base] = -0.5
                            ans[partner] = ans[base] + 1
                elif len(tree_adj_down[base]) == 2:
                    part_ident_l, part_ident_r = sorted(tree_adj_down[base], key = eval_order)
                    for dir, part_ident in [(-1, part_ident_l), (1, part_ident_r)]:
                        if len(tree_adj_up[part_ident]) == 2: #if there are exactly two parents. other possible cases are 1 parent (base) or more than 2 (which is too weird to bother handling here)
                            parent_1, parent_2 = tree_adj_up[part_ident]
                            if base == parent_1:
                                partner = parent_2
                            else:
                                assert base == parent_2
                                partner = parent_1
                            ans[partner] = ans[base] + dir

            return ans


        def generate_pos_up(base, existing, left_drop, right_drop, do_left_drop, do_right_drop):
            assert base in existing
            assert type(do_left_drop) == type(do_right_drop) == bool

            def inc_drop(drop):
                if drop is None:
                    return None
                else:
                    return drop + 1
                
            #start by computing the part lying entirely above the base node
            ups = tree_adj_up[base]
            if len(ups) == 0:
                return existing
        
            if len(ups) == 1:
                up = ups[0]
                up_part = generate_pos_up(up, {up : 0.0}, inc_drop(left_drop), inc_drop(right_drop), False, False)
            else:
                left = ups[0]
                mids = ups[1:-1]
                right = ups[1]

                up_parts = []
                up_parts.append(generate_pos_up(left, {left : 0.0}, inc_drop(left_drop), 0, False, True))
                for mid in mids:
                    up_parts.append(generate_pos_up(mid, {mid : 0.0}, 0, 0, True, True))
                up_parts.append(generate_pos_up(right, {right : 0.0}, 0, inc_drop(right_drop), True, False))

                up_part = stack_together(up_parts)

            up_poses = [up_part[up] for up in tree_adj_up[base]]
            d_min = min(up_poses)
            d_max = max(up_poses)
            off = 0.5 * (d_min + d_max)
            up_part = {ident : up_part[ident] - off + existing[base] for ident in up_part}
            ans = existing | up_part

            left_dangles = []
            right_dangles = []

            #now add the bit which dangle off the left and right sides after going up from the base node
            #traverse up the left side of nodes
            #for each node, look at all its children other than the one we came from
            #add the downwards positions of each child, but only as far as left_drop/right_drop allow us to go

            if do_left_drop:
                path = [base]
                while True:
                    if path[-1] in tree_adj_up:
                        if len(tree_adj_up[path[-1]]) > 0:
                            path.append(tree_adj_up[path[-1]][0])
                            continue
                    break

                for i in range(0, len(path) - 1):
                    bottom = path[i]
                    top = path[i + 1]
                    drops = [ident for ident in tree_adj_down[top] if eval_order(ident) < eval_order(bottom)]
                    assert not bottom in drops
                    for drop in drops:
                        ans = stack_right(generate_pos_down(drop, left_drop + i), ans)
                        assert base in ans

            if do_right_drop:
                path = [base]
                while True:
                    if path[-1] in tree_adj_up:
                        if len(tree_adj_up[path[-1]]) > 0:
                            path.append(tree_adj_up[path[-1]][-1])
                            continue
                    break

                for i in range(0, len(path) - 1):
                    bottom = path[i]
                    top = path[i + 1]
                    drops = [ident for ident in tree_adj_down[top] if eval_order(bottom) < eval_order(ident)]
                    assert not bottom in drops
                    for drop in drops:
                        ans = stack_left(ans, generate_pos_down(drop, right_drop + i))
                        assert base in ans

            off = ans[base]
            ans = {ident : pos - off for ident, pos in ans.items()}
                
            return ans


        def generate_pos_root(root):
            ans = generate_pos_down(root, math.inf)
            ans = generate_pos_up(root, ans, math.inf, math.inf, True, True)
            return ans
        
        tree_x = generate_pos_root(root)
        tree_pos = {ident : (tree_x[ident], tree_heights[ident]) for ident in tree_x}

        #generate edges
        tree_edges = set()
        for ident_1 in tree_x:
            for ident_2 in tree_adj_up[ident_1]:
                if ident_2 in tree_x:
                    tree_edges.add((ident_1, ident_2))

        tree_extra_edges = set()
        for ident_1 in tree_x:
            for ident_2 in self.adj_up[ident_1]:
                if ident_2 in tree_x:
                    if not (ident_1, ident_2) in tree_edges:
                        tree_extra_edges.add((ident_1, ident_2))
                

        return tree_pos, tree_edges, tree_extra_edges




        