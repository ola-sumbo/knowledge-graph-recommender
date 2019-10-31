import torch
import torch.nn as nn
import torch.nn.functional as F

class KPRN(nn.Module):

    def __init__(self, e_emb_dim, t_emb_dim, r_emb_dim, hidden_dim, vocab_size, tagset_size):
        super(KPRN, self).__init__()
        self.hidden_dim = hidden_dim

        self.entity_embeddings = nn.Embedding(vocab_size, e_emb_dim)
        self.type_embeddings = nn.Embedding(vocab_size, t_emb_dim)
        self.rel_embeddings = nn.Embedding(vocab_size, r_emb_dim)

        # The LSTM takes word embeddings as inputs, and outputs hidden states
        # with dimensionality hidden_dim.
        self.lstm = nn.LSTM(e_emb_dim + t_emb_dim + r_emb_dim, hidden_dim)

        # The linear layer that maps from hidden state space to to tags
        self.linear1 = nn.Linear(hidden_dim, hidden_dim)
        self.linear2 = nn.Linear(hidden_dim, tagset_size)

    def forward(self, paths, path_lengths):
        #transpose, so entities 1st row, types 2nd row, and relations 3nd (these are dim 1 and 2 since batch is 0)
        #this could just be the input if we want
        t_paths = torch.transpose(paths, 1, 2)

        #then concatenate embeddings, batch is index 0, so selecting along index 1
        #right now we do fetch embedding for padding tokens, but that these aren't used
        entity_embed = self.entity_embeddings(t_paths[:,0,:])
        type_embed = self.type_embeddings(t_paths[:,1,:])
        rel_embed = self.rel_embeddings(t_paths[:,2,:])
        triplet_embed = torch.cat((entity_embed, type_embed, rel_embed), 2) #concatenates lengthwise

        #we need dimensions to be input size x batch_size x embedding dim, so transpose first 2 dim
        batch_sec_embed = torch.transpose(triplet_embed, 0 , 1)

        #pack padded sequences, so we don't do extra computation
        packed_embed = nn.utils.rnn.pack_padded_sequence(batch_sec_embed, path_lengths)

        #last_out is the output state before padding for each path, since we only want final output
        packed_out, (last_out, _) = self.lstm(packed_embed)

        ##can visualize unpacked seq to see that last_out is what we want
        #lstm_out, lstm_out_lengths = nn.utils.rnn.pad_packed_sequence(packed_out)
        #print(lstm_out, lstm_out_lengths)

        #pass through linear layers
        tag_scores = self.linear2(F.relu(self.linear1(last_out[-1])))

        #Paper uses relu as final activation, but for Pytorch's nllloss it seems like we need a softmax layer
        #to convert to probability distribution?
        #return F.relu(tag_score)
        return F.log_softmax(tag_scores, dim=1)

    #TODO: construct weighted pooling function, that can be called in predictoe