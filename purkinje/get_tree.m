function [adj,distance, terminal] = get_tree(E,N,surface,C)



n = length(N);
adj = zeros(n);
unseen = ones(n,1);
admisable = unique(E(surface,:));

dist = sum(((N(admisable,:) - ones(length(admisable),1)*C).^2)');
[val,idx] = min(dist);

%[val,idx] = max(N(admisable,3))
root = admisable(idx);
size(admisable)
Q = root;
unseen(root) = 0;
distance = zeros(length(N),1);
terminal = zeros(length(N),1);
while ~isempty(Q)
   % use first node in queue as root for this subtree 
   root = Q(1); Q = Q(2:end); 
   % find the neighbours of this node:
   e = [find(E(:,1)==root);find(E(:,2)==root);find(E(:,3)==root)];
   nodes = unique(E(e,:));
   % keep only unseen nodes, among the admisable ones:

   nodes  = intersect(intersect(admisable,find(unseen)), nodes);

   % only consider nodes that are more apical than the root node:

   nodes = nodes(find(N(root,3)>N(nodes,3)));


   % mark as terminal if no nodes will be added:
   if isempty(nodes)
       terminal(root) = 1;
   end
   for i = 1:min(3,length(nodes)) % take the first nodes for now
       node = nodes(i);
       adj(root, node) = 1; % add an edge between root and node
       Q = [Q; node]; % add this node for further exploration
       unseen(node)=0; % make sure we don't add it again
       dist = sqrt(sum((N(root,:)-N(node,:)).^2));
       distance(node) = distance(root) + dist;
   end
   

end


adj = sparse(adj);