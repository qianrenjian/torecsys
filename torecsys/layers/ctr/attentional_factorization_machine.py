from torecsys.utils.decorator import jit_experimental
import torch
import torch.nn as nn
from typing import Tuple


class AttentionalFactorizationMachineLayer(nn.Module):
    r"""Layer class of Attentional Factorization Machine (AFM) to calculate interaction between each 
    pair of features by using element-wise product (i.e. Pairwise Interaction Layer), compressing 
    interaction tensors to a single representation. The output shape is (B, 1, E).
    
    :Reference:

    #. `Jun Xiao et al, 2017. Attentional Factorization Machines: Learning the Weight of Feature Interactions via Attention Networks∗ <https://arxiv.org/abs/1708.04617>`_.

    """
    @jit_experimental
    def __init__(self, 
                 embed_size: int,
                 num_fields: int,
                 attn_size : int,
                 dropout_p : float = 0.1):
        r"""Initialize AttentionalFactorizationMachineLayer
        
        Args:
            embed_size (int): Size of embedding tensor
            num_fields (int): Number of inputs' fields
            attn_size (int): Size of attention layer
            dropout_p (float, optional): Probability of Dropout in AFM. 
                Defaults to 0.1.
        
        Arguments:
            attention (torch.nn.Sequential): Sequential of Attention-layers.
            row_idx (list): 1st indices to index inputs in 2nd dimension for inner product.
            col_idx (list): 2nd indices to index inputs in 2nd dimension for inner product.
            dropout (torch.nn.Module): Dropout layer.

        """
        # refer to parent class
        super(AttentionalFactorizationMachineLayer, self).__init__()

        # initialize sequential for Attention
        self.attention = nn.Sequential()

        # add modules to sequential of Attention
        self.attention.add_module("linear1", nn.Linear(embed_size, attn_size))
        self.attention.add_module("activation1", nn.ReLU())
        self.attention.add_module("out_proj", nn.Linear(attn_size, 1))
        self.attention.add_module("softmax1", nn.Softmax(dim=1))
        self.attention.add_module("dropout1", nn.Dropout(dropout_p))

        # create row_idx and col_idx to index inputs
        self.row_idx = []
        self.col_idx = []
        for i in range(num_fields - 1):
            for j in range(i + 1, num_fields):
                self.row_idx.append(i)
                self.col_idx.append(j)
        
        # initialize dropout layer before return
        self.dropout = nn.Dropout(dropout_p)
    
    def forward(self, emb_inputs: torch.Tensor) -> Tuple[torch.Tensor]:
        r"""Forward calculation of AttentionalFactorizationMachineLayer

        Args:
            emb_inputs (T), shape = (B, N, E), dtype = torch.float: Embedded features tensors.
        
        Returns:
            Tuple[T], shape = ((B, 1, E) (B, NC2, 1)), dtype = torch.float: Output of AttentionalFactorizationMachineLayer and Attention weights.
        """
        # calculate inner product between each field,
        # inner's shape = (B, NC2, E)
        inner = emb_inputs[:, self.row_idx] * emb_inputs[:, self.col_idx]

        # calculate attention scores by inner product,
        # scores' shape = (B, NC2, 1)
        attn_scores = self.attention(inner)
        
        # apply attention scores on inner-product
        outputs = torch.sum(attn_scores * inner, dim=1)

        # apply dropout before return
        outputs = self.dropout(outputs)
        return outputs.unsqueeze(1), attn_scores
    