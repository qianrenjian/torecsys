from ..logging import TqdmHandler
from torecsys.functional.regularization import Regularizer
from torecsys.inputs.base import _Inputs
from torecsys.models import _Model
from logging import Logger
from os import path
from pathlib import Path
from texttable import Texttable
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from tqdm.autonotebook import tqdm
from typing import Dict
import warnings


class Trainer(object):
    def __init__(self,
                 inputs_wrapper : _Inputs,
                 model          : _Model,
                 regularizer    : Regularizer = Regularizer(0.1, 2),
                 loss           : type = nn.MSELoss,
                 optimizer      : type = optim.AdamW,
                 epochs         : int = 10,
                 verboses       : int = 2,
                 log_step       : int = 500,
                 log_dir        : str = "logdir"):
        
        # set embeddings and model of the trainer
        self.embeddings = inputs_wrapper
        self.model = model

        # set regularizer, loss, optimizer, ...
        self.regularizer = regularizer
        self.loss = loss()
        self.parameters = list(self.embeddings.parameters()) + list(self.model.parameters())
        self.optimizer = optimizer(self.parameters)
        self.epochs = epochs
        self.verboses = verboses
        self.log_step = log_step

        # count number of parameters in model
        self.num_params = sum(p.numel() for p in self.parameters if p.requires_grad)

        # streaming log in tqdm will be initialized 
        if verboses >= 1:
            # initialize logger of trainer
            self.logger = Logger("trainer")

            # set logger config, including level and handler
            self.logger.setLevel("DEBUG")
            handelr = TqdmHandler()
            self.logger.addHandler(handelr)

            self.logger.info("logger have been initialized.")
        
        # log in tensorboard will be initialized 
        if verboses >= 2:
            # store the path of log dir
            self.log_dir = path.join(path.dirname(__file__), log_dir)

            # create the folder if log_dir is not exist 
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # intitialize tensorboard summary writer with given log_dir
            self.writer = SummaryWriter(log_dir=log_dir)

            # print the summary writer's location
            self.logger.info("tensorboard summary writter have been created and the log directory is set to %s." % (self.log_dir))

        print(self._describe())
    
    def _add_embedding(self):
        return 

    def _add_graph(self, 
                   samples_inputs : Dict[str, torch.Tensor], 
                   verbose        : bool = True):
        r"""Add graph data to summary.
        
        Args:
            samples_inputs (Dict[str, T]): A dictionary of variables to be fed.
            verboses (bool, optional): Whether to print graph structure in console. Defaults to True.
        """
        raise NotImplementedError("ERROR!!!")
        if self.verboses >= 2:
            embed_inputs = self.embeddings(samples_inputs)
            self.writer.add_graph(self.model, **embed_inputs, verbose=verbose)
        else:
            if self.verboses >= 1:
                self.logger.warn("_add_graph only can be called when self.verboses >= 2.")
            else:
                warnings.warn("_add_graph only can be called when self.verboses >= 2.")
        
    def _describe(self):
        r"""Show summary of trainer
        """
        # getattr from self 
        embed_name = self.embeddings.__class__.__name__ if getattr(self, "embeddings", None) is not None else None
        model_name = self.model.__class__.__name__ if getattr(self, "model", None) is not None  else None
        loss_name = self.loss.__class__.__name__ if getattr(self, "loss", None) is not None  else None
        optim_name = self.optimizer.__class__.__name__ if getattr(self, "optimizer", None) is not None  else None
        regul_norm = self.regularizer.norm if getattr(self, "regularizer", None) is not None  else None
        regul_lambda = self.regularizer.weight_decay if getattr(self, "regularizer", None) is not None  else None
        epochs = self.epochs if getattr(self, "epochs", None) is not None  else None
        logdir = self.log_dir if getattr(self, "log_dir", None) is not None  else None
        
        # initialize _vars of parameters 
        _vars = {
            "embeddings"    : embed_name,
            "model"         : model_name,
            "loss"          : loss_name,
            "optimizer"     : optim_name,
            "reg norm"      : regul_norm,
            "reg lambda"    : regul_lambda,
            "num of epochs" : epochs,
            "log directory" : logdir
        }
        
        # initialize and configurate Texttable
        t = Texttable()
        t.set_deco(Texttable.BORDER)
        t.set_cols_align(["l", "l"])
        t.set_cols_valign(["t", "t"])

        # append data to texttable
        t.add_rows(
            [["Name: ", "Value: "]] + \
            [[k.capitalize(), v] for k, v in _vars.items() if v is not None]
        )

        return t.draw()
        
    def _iterate(self, batch_inputs: Dict[str, torch.Tensor], labels: torch.Tensor) -> torch.Tensor:
        # zero the parameter gradients
        self.optimizer.zero_grad()
        
        # calculate forward prediction
        embed_inputs = self.embeddings(batch_inputs)
        outputs = self.model(**embed_inputs)

        # calculate loss and regularized loss
        loss = self.loss(outputs, labels)
        if self.regularizer is not None:
            named_params = list(self.embeddings.named_parameters()) + list(self.model.named_parameters())
            print(named_params)
            reg_loss = self.regularizer(named_params)
            loss += reg_loss

        # calculate backward and optimize 
        loss.backward()
        self.optimizer.step()

        # return loss to log stream and tensorboard
        return loss
    
    def fit(self, dataloader: torch.utils.data.DataLoader):
        # initialize global_step = 0 for logging
        global_step = 0

        # number of batches
        num_batch = len(batch_inputs)

        # loop through n epochs
        for epoch in self.epochs:
            # initialize loss variables to store aggregated loss
            steps_loss = 0.0
            epoch_loss = 0.0

            # logging of the epoch
            if verboses >= 1:
                self.logger.info("Epoch %s / %s:" % (epoch + 1, self.epochs))
            
            # initialize progress bar of dataloader of this epoch
            pbar = tqdm(dataloader, desc="step loss : ??.????", ncols=100, ascii=True)

            for i, (batch_inputs, labels) in enumerate(pbar):
                # iteration of the batch
                loss = self._iterate(batch_inputs, labels)
                
                # add step loss to steps_loss and epoch_loss
                loss_val = loss.item()
                steps_loss += loss_val
                epoch_loss += loss_val

                # set loss to the description of pbar
                pbar.set_description("step loss : %.4f" % (loss_val))

                # log for each y steps
                if global_step % self.log_step == 0:
                    if self.verboses >= 1:
                        self.logger.debug("step avg loss : %.4f" % (steps_loss / self.log_step))
                    if self.verboses >= 2:
                        self.writer.add_scalar("training/steps_avg_loss", steps_loss / self.log_step, global_step=global_step)    
                    steps_loss = 0.0

                global_step += 1

            # log for each epoch
            if self.verboses >= 1:
                self.logger.info("epoch avg loss : %.4f" % (epoch_loss / num_batch))
            
            if self.verboses >= 2:
                self.writer.add_scalar("training/epoch_avg_loss", epoch_loss / num_batch, global_step=epoch)

    def predict(self, batch):
        return
    
    def save(self):
        return
    
    def load(self):
        return
    