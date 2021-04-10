from pdb import set_trace as T
from gym import spaces
import numpy as np
from stable_baselines3.common.policies import ActorCriticPolicy, MlpExtractor, ActorCriticCnnPolicy
from stable_baselines3.common.distributions import MultiCategoricalDistribution, CategoricalDistribution, Distribution, StateDependentNoiseDistribution, DiagGaussianDistribution, get_action_dim
import torch as th
from torch import nn
from typing import Any, Dict, List, Optional, Tuple, Type, Union

conv = th.nn.Conv2d
linear = th.nn.Linear
conv_to_fc = th.nn.Flatten

#TODO: Finish porting models to pytorch
#TODO: Experiment with different architectures, self-attention..?

#def Cnn1(image, **kwargs):
#    activ = tf.nn.relu
#    layer_1 = activ(conv(image, 32, filter_size=3, stride=1, init_scale=np.sqrt(2), **kwargs))
#    layer_2 = activ(conv(layer_1, 'c2', n_filters=64, filter_size=3, stride=1, init_scale=np.sqrt(2), **kwargs))
#    layer_3 = activ(conv(layer_2, 'c3', n_filters=64, filter_size=3, stride=1, init_scale=np.sqrt(2), **kwargs))
#    layer_3 = conv_to_fc(layer_3)
#
#    return activ(linear(layer_3, 'fc1', n_hidden=512, init_scale=np.sqrt(2)))

class Cnn1(th.nn.Module):
    def __init__(self, observation_space, **kwargs):
        super().__init__()
        n_chan = observation_space.shape[2]
        self.features_dim = 512
        self.cnn = nn.Sequential(
            conv(n_chan, 32, kernel_size=3, stride=1, **kwargs),
            nn.ReLU(),
            conv(32, 64, kernel_size=3, stride=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, **kwargs),
            nn.ReLU(),
            nn.Flatten(),
        )

        # Compute shape by doing one forward pass
        with th.no_grad():
            n_flatten = self.cnn(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float()).shape[1]
        self.l1 = linear(n_flatten, 512)

    def forward(self, image):
        image = image.permute(0, 3, 1, 2)
        x = self.cnn(image)
        x = self.l1(x)

        return x

class FullCnn(th.nn.Module):
    ''' Like the old FullCnn2, for wide representations with binary or zelda.'''
    def __init__(self, observation_space, n_tools, **kwargs):
        super().__init__()
        self.features_dim = n_tools
        n_chan = observation_space.shape[2]
        act = nn.functional.relu
        self.cnn = nn.Sequential(
            conv(n_chan, 32, kernel_size=3, stride=1, padding=1,  **kwargs),
            nn.ReLU(),
            conv(32, 64, kernel_size=3, stride=1, padding=1,  **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, n_tools, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
        )
        self.act_head = nn.Sequential(
        )

        # Compute shape by doing one forward pass
#       with th.no_grad():
#           _, _, width, height = self.cnn(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float()).shape
#           assert width == height
#           n_shrink = np.log2(width)
#           assert n_shrink % 1 == 0
#           n_shrink = int(n_shrink)

        self.val_shrink = nn.Sequential(
            conv(n_tools, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=1, stride=1, padding=0, **kwargs),
            nn.ReLU(),
        )
        with th.no_grad():
            n_flatten = self.val_shrink(self.cnn(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float())).view(-1).shape[0]

        self.val_head = nn.Sequential(
            nn.Flatten(),
            linear(n_flatten, 1)
        )

    def forward(self, image):
        image = image.permute(0, 3, 1, 2)
        x = self.cnn(image)
        act = self.act_head(x)
        val = self.val_head(self.val_shrink(x))

        return act, val

class NCA(th.nn.Module):
    '''Big dumb ugly NCA that crashes early on so far.'''
    def __init__(self, observation_space, n_tools, **kwargs):
        super().__init__()
        self.features_dim = n_tools
        n_chan = observation_space.shape[2]
        act = nn.functional.relu
        self.cnn = nn.Sequential(
            conv(n_chan, 32, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(32, 64, kernel_size=3, stride=1, padding=1,  **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, n_tools, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
        )
        self.act_head = nn.Sequential(
            nn.Flatten(2),
        )

        # Compute shape by doing one forward pass
#       with th.no_grad():
#           _, _, width, height = self.cnn(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float()).shape
#           assert width == height
#           n_shrink = np.log2(width)
#           assert n_shrink % 1 == 0
#           n_shrink = int(n_shrink)

        self.val_shrink = nn.Sequential(
            conv(n_tools, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=1, stride=1, padding=0, **kwargs),
            nn.ReLU(),
        )
        with th.no_grad():
            n_flatten = self.val_shrink(self.cnn(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float())).view(-1).shape[0]

        self.val_head = nn.Sequential(
            nn.Flatten(),
            linear(n_flatten, 1)
        )

    def forward(self, image):
        image = image.permute(0, 3, 1, 2)
        x = self.cnn(image)
        act = self.act_head(x)
        act = act.permute(0, 2, 1)
        val = self.val_head(self.val_shrink(x))

        return act, val

#@title Minimalistic Neural CA
class CA_0(th.nn.Module):
    def __init__(self, observation_space, hidden_n=96, n_tools=None,  **kwargs):
        super().__init__()
        self.n_tools = n_tools
        self.ident = th.tensor([[0.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,0.0]])
        self.sobel_x = th.tensor([[-1.0,0.0,1.0],[-2.0,0.0,2.0],[-1.0,0.0,1.0]])/8.0
        self.lap = th.tensor([[1.0,2.0,1.0],[2.0,-12,2.0],[1.0,2.0,1.0]])/16.0
        self.filters = th.stack([self.ident, self.sobel_x, self.sobel_x.T, self.lap])

        # dummy
        self.features_dim = n_tools
        self.chn = observation_space.shape[2]
        # it's dumb that we're applying sobel and laplace filters to our ParamRew observation, which is the same acrsss the map, so we add this lil' embedding layer
        self.w1 = th.nn.Conv2d(self.chn*4, hidden_n, 1)
        self.w2 = th.nn.Conv2d(hidden_n, n_tools, 1, bias=False)
#       self.w2.weight.data.zero_()

        self.val_shrink = nn.Sequential(
            conv(n_tools, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=1, stride=1, padding=0, **kwargs),
            nn.ReLU(),
        )
        with th.no_grad():
            n_flatten = self.val_shrink(self.w2(self.w1(self.perception(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float())))).view(-1).shape[0]
        if th.cuda.is_available():
            self.filters = self.filters.cuda()

        self.val_head = nn.Sequential(
            nn.Flatten(),
            linear(n_flatten, 1)
        )

    def forward(self, x, update_rate=0.05):
        x = x.permute(0, 3, 1, 2)
        y = self.perception(x)
        y = th.sigmoid(self.w2(th.relu(self.w1(y))))
        b, c, h, w = y.shape
        # FIXME: should not be calling cuda here :(
        update_mask = (th.rand(b, 1, h, w) < update_rate)
        if th.cuda.is_available():
            update_mask = update_mask.cuda()
        act = x[:,-self.n_tools:] * (update_mask == False) + y * update_mask
       #update_mask = (th.rand(b, 1, h, w)+update_rate).floor()
       #act = x[:,-self.n_tools:]+y*update_mask.cuda()
        val = self.val_head(self.val_shrink(act))
        
        return act, val

    def perchannel_conv(self, x, filters):
        '''filters: [filter_n, h, w]'''
        b, ch, h, w = x.shape
        # TODO: Don't assume the control observations will come first! Do something smart, like pass a dictionary of np arrays. Being hackish now for backward compatibility.
        y = x.reshape(b*ch, 1, h, w)
        y = th.nn.functional.pad(y, [1, 1, 1, 1])
        y = th.nn.functional.conv2d(y, filters[:,None])
        return y.reshape(b, -1, h, w)

    def perception(self, x):
        return self.perchannel_conv(x, self.filters)

#@title Minimalistic Neural CA
class CA_1(th.nn.Module):
    def __init__(self, observation_space, n_tools=None, hidden_n=96, **kwargs):
        super().__init__()
        self.n_tools = n_tools
        self.ident = th.tensor([[0.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,0.0]])
        self.sobel_x = th.tensor([[-1.0,0.0,1.0],[-2.0,0.0,2.0],[-1.0,0.0,1.0]])/8.0
        self.lap = th.tensor([[1.0,2.0,1.0],[2.0,-12,2.0],[1.0,2.0,1.0]])/16.0
        self.filters = th.stack([self.ident, self.sobel_x, self.sobel_x.T, self.lap])

        # dummy
        self.features_dim = n_tools
        self.chn = observation_space.shape[2]
        # it's dumb that we're applying sobel and laplace filters to our ParamRew observation, which is the same acrsss the map, so we add this lil' embedding layer
        self.w1 = th.nn.Conv2d(self.chn*4, hidden_n, 1)
        self.w2 = th.nn.Conv2d(hidden_n, n_tools, 1, bias=False)
        self.w2.weight.data.zero_()

        self.c2 = nn.Sequential(
            conv(self.chn, hidden_n, kernel_size=7, stride=1, padding=3, **kwargs),
            nn.ReLU(),
            conv(hidden_n, hidden_n, kernel_size=5, stride=1, padding=2, **kwargs),
            nn.ReLU(),
            conv(hidden_n, hidden_n, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(hidden_n, n_tools, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.Sigmoid(),
        )

        self.val_shrink = nn.Sequential(
            conv(n_tools, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=1, stride=1, padding=0, **kwargs),
            nn.ReLU(),
        )
        with th.no_grad():
            n_flatten = self.val_shrink(self.w2(self.w1(self.perception(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float())))).view(-1).shape[0]
        if th.cuda.is_available():
            self.filters = self.filters.cuda()

        self.val_head = nn.Sequential(
            nn.Flatten(),
            linear(n_flatten, 1)
        )

    def forward(self, x, update_rate=1.0):
        x = x.permute(0, 3, 1, 2)
        y = self.perception(x)
#       y = self.w2(th.relu(self.w1(y)))
        y = self.w2(th.sigmoid(self.w1(y)))
        z = self.c2(x)
        b, c, h, w = y.shape
        # FIXME: should not be calling cuda here :(
        update_mask = (th.rand(b, 1, h, w) < update_rate)
        if th.cuda.is_available():
            update_mask = update_mask.cuda()
        act = x[:,-self.n_tools:] * (update_mask == False) + y * update_mask
        act = (act + z) / 2
       #update_mask = (th.rand(b, 1, h, w)+update_rate).floor()
       #act = x[:,-self.n_tools:]+y*update_mask.cuda()
        val = self.val_head(self.val_shrink(act))
        
        return act, val

    def perchannel_conv(self, x, filters):
        '''filters: [filter_n, h, w]'''
        b, ch, h, w = x.shape
        # TODO: Don't assume the control observations will come first! Do something smart, like pass a dictionary of np arrays. Being hackish now for backward compatibility.
        y = x.reshape(b*ch, 1, h, w)
        y = th.nn.functional.pad(y, [1, 1, 1, 1])
        y = th.nn.functional.conv2d(y, filters[:,None])
        return y.reshape(b, -1, h, w)

    def perception(self, x):
        return self.perchannel_conv(x, self.filters)

class CA_2(th.nn.Module):
    def __init__(self, observation_space, n_tools=None, hidden_n=96, **kwargs):
        super().__init__()
        self.n_tools = n_tools
        self.map_width = observation_space.shape[0]
        self.ident = th.tensor([[0.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,0.0]])
        self.sobel_x = th.tensor([[-1.0,0.0,1.0],[-2.0,0.0,2.0],[-1.0,0.0,1.0]])/8.0
        self.lap = th.tensor([[1.0,2.0,1.0],[2.0,-12,2.0],[1.0,2.0,1.0]])/16.0
        self.filters = th.stack([self.ident, self.sobel_x, self.sobel_x.T, self.lap])

        # dummy
        self.features_dim = n_tools
        self.chn = observation_space.shape[2]
        # it's dumb that we're applying sobel and laplace filters to our ParamRew observation, which is the same acrsss the map, so we add this lil' embedding layer
        self.w1 = th.nn.Conv2d(self.chn*4, hidden_n, 1)
        self.w2 = th.nn.Conv2d(hidden_n, n_tools, 1, bias=False)
        self.w2.weight.data.zero_()

        self.c2 = nn.Sequential(
            conv(self.chn, hidden_n, kernel_size=7, stride=1, padding=3, **kwargs),
            nn.ReLU(),
            conv(hidden_n, hidden_n, kernel_size=5, stride=1, padding=2, **kwargs),
            nn.ReLU(),
            conv(hidden_n, hidden_n, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(hidden_n, n_tools, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.Sigmoid(),
        )

        self.encode = nn.Sequential(
            conv(self.chn, 64, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 32, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            conv(32, 32, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
            )

        with th.no_grad():
            n_hidden = self.encode(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float()).view(-1).shape[0]

        n_hidden_out = int(32 * observation_space.shape[0] / 4 * observation_space.shape[0] / 4)
        self.l1 = linear(n_hidden, n_hidden_out)
        self.l2 = linear(n_hidden_out, n_hidden)

        self.decode = nn.Sequential(
         #  nn.ConvTranspose2d(32, 32, kernel_size=3, stride=2, padding=1, output_padding=1, **kwargs),
         #  nn.ReLU(),
         #  nn.ConvTranspose2d(32, 64, kernel_size=3, stride=2, padding=1, output_padding=1, **kwargs),
         #  nn.ReLU(),
         #  nn.ConvTranspose2d(64, n_tools, kernel_size=3, stride=2, padding=1, output_padding=1, **kwargs),
         #  nn.ReLU(),
            conv(32, n_tools, kernel_size=3, stride=1, padding=1, **kwargs),
            nn.ReLU(),
        )


        self.val_shrink = nn.Sequential(
            conv(n_tools, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=3, stride=2, padding=1, **kwargs),
            nn.ReLU(),
            conv(64, 64, kernel_size=1, stride=1, padding=0, **kwargs),
            nn.ReLU(),
        )
        with th.no_grad():
            n_flatten = self.val_shrink(self.w2(self.w1(self.perception(th.as_tensor(observation_space.sample()[None]).permute(0, 3, 1, 2).float())))).view(-1).shape[0]
        if th.cuda.is_available():
            self.filters = self.filters.cuda()

        self.val_head = nn.Sequential(
            nn.Flatten(),
            linear(n_flatten, 1)
        )

    def forward(self, x, update_rate=1.0):
        x = x.permute(0, 3, 1, 2)
        y = self.perception(x)
#       y = self.w2(th.relu(self.w1(y)))
        y = self.w2(th.sigmoid(self.w1(y)))
        z = self.c2(x)
        v = self.encode(x)
        hidden_2d_shape = v.shape
        v = v.reshape(v.shape[0], -1)
        v = th.tanh(self.l1(v))
        v = th.tanh(self.l2(v))
#       v = v.reshape(hidden_2d_shape)
        v = v.reshape(v.shape[0], 32, int(self.map_width/1), int(self.map_width/1))
        v = self.decode(v)
        b, c, h, w = y.shape
        # FIXME: should not be calling cuda here :(
        if th.cuda.is_available():
            update_mask = (th.rand(b, 1, h, w) < update_rate).cuda()
        act = x[:,-self.n_tools:] * (update_mask == False) + y * update_mask
        act = (act + z + v) / 3
       #update_mask = (th.rand(b, 1, h, w)+update_rate).floor()
       #act = x[:,-self.n_tools:]+y*update_mask.cuda()
        val = self.val_head(self.val_shrink(act))
        
        return act, val

    def perchannel_conv(self, x, filters):
        '''filters: [filter_n, h, w]'''
        b, ch, h, w = x.shape
        # TODO: Don't assume the control observations will come first! Do something smart, like pass a dictionary of np arrays. Being hackish now for backward compatibility.
        y = x.reshape(b*ch, 1, h, w)
        y = th.nn.functional.pad(y, [1, 1, 1, 1])
        y = th.nn.functional.conv2d(y, filters[:,None])
        return y.reshape(b, -1, h, w)

    def perception(self, x):
        return self.perchannel_conv(x, self.filters)


#    def seed(self, n, sz=128):
#        return th.zeros(n, self.chn, sz, sz)



class NoDenseMultiCategoricalDistribution(MultiCategoricalDistribution):
    """
    MultiCategorical distribution for multi discrete actions.

    :param action_dims: List of sizes of discrete action spaces
    """

    def __init__(self, action_dims: List[int]):
        super(NoDenseMultiCategoricalDistribution, self).__init__(action_dims)
        self.action_dims = action_dims
        self.distributions = None

    def proba_distribution_net(self, latent_dim: int) -> nn.Module:
        """
        Create the layer that represents the distribution:
        it will be the logits (flattened) of the MultiCategorical distribution.
        You can then get probabilities using a softmax on each sub-space.

        :param latent_dim: Dimension of the last layer
            of the policy network (before the action layer)
        :return:
        """

#       action_logits = nn.Linear(latent_dim, sum(self.action_dims))
        action_logits = IdentityActModule()
        return action_logits

    def sample(self) -> th.Tensor:
        actions = th.stack([dist.sample() for dist in self.distributions], dim=1)
#       actions = th.stack([dist.logits.argmax(dim=1) for dist in self.distributions], dim=1)
        return actions

class NoDenseCategoricalDistribution(CategoricalDistribution):
    """
    MultiCategorical distribution for multi discrete actions.

    :param action_dims: List of sizes of discrete action spaces
    """

    def __init__(self, action_dims: List[int]):
        super(NoDenseCategoricalDistribution, self).__init__(action_dims)
        self.action_dims = action_dims
        self.distributions = None

    def proba_distribution_net(self, latent_dim: int) -> nn.Module:
        """
        Create the layer that represents the distribution:
        it will be the logits (flattened) of the MultiCategorical distribution.
        You can then get probabilities using a softmax on each sub-space.

        :param latent_dim: Dimension of the last layer
            of the policy network (before the action layer)
        :return:
        """

#       action_logits = nn.Linear(latent_dim, sum(self.action_dims))
        action_logits = IdentityActModule()
        return action_logits

    def sample(self):
        ret = super().sample()
        return ret

################################################################################
#   Boilerplate policy classes
################################################################################

class CustomPolicyBigMap(ActorCriticCnnPolicy):
    def __init__(self, *args, **kwargs):
        super(CustomPolicyBigMap, self).__init__(*args, **kwargs, features_extractor_class=Cnn1)#, feature_extraction="cnn")
import gym

def make_proba_distribution(
    action_space: gym.spaces.Space, use_sde: bool = False, dist_kwargs: Optional[Dict[str, Any]] = None
) -> Distribution:
    """
    Return an instance of Distribution for the correct type of action space

    :param action_space: the input action space
    :param use_sde: Force the use of StateDependentNoiseDistribution
        instead of DiagGaussianDistribution
    :param dist_kwargs: Keyword arguments to pass to the probability distribution
    :return: the appropriate Distribution object
    """
    if dist_kwargs is None:
        dist_kwargs = {}

    if isinstance(action_space, gym.spaces.MultiDiscrete):
        return NoDenseMultiCategoricalDistribution(action_space.nvec)
    elif isinstance(action_space, gym.spaces.Discrete):
        return NoDenseCategoricalDistribution(action_space.n)
    if isinstance(action_space, spaces.Box):
        assert len(action_space.shape) == 1, "Error: the action space must be a vector"
        cls = StateDependentNoiseDistribution if use_sde else DiagGaussianDistribution
        return cls(get_action_dim(action_space), **dist_kwargs)

class IdentityActModule(th.nn.Module):
    def __init__(self):
        super().__init__()
        self.flatten = th.nn.Flatten()

    def forward(self, latents):
        latent_pi, latent_val = latents
        #FIXME: eeksauce
        latent_pi = latent_pi.permute(0, 2, 3, 1)
        ret = self.flatten(latent_pi)
        return ret
    

class IdentityValModule(th.nn.Module):
    def __init__(self):
        super().__init__()
        self.flatten = th.nn.Flatten()

    def forward(self, latents):
        latent_pi, latent_val = latents
        ret = self.flatten(latent_val)
        return ret

class WidePolicy(ActorCriticCnnPolicy):
    def __init__(self, 
            observation_space,
            action_space,
            lr_schedule,
            **kwargs):
        n_tools = kwargs.pop("n_tools")
        features_extractor_kwargs = {'n_tools': n_tools}
        super(WidePolicy, self).__init__(observation_space, action_space, lr_schedule, **kwargs, net_arch=None, features_extractor_class=FullCnn, features_extractor_kwargs=features_extractor_kwargs)
        # funky for CA type action
        use_sde = False
        dist_kwargs = None
        self.action_dist = make_proba_distribution(action_space, use_sde=use_sde, dist_kwargs=dist_kwargs)
        self._build(lr_schedule)
        self.action_net = IdentityActModule()
        self.value_net = IdentityValModule()

class CApolicy(ActorCriticCnnPolicy):
    def __init__(self, 
            observation_space,
            action_space,
            lr_schedule,
            **kwargs):
        n_tools = kwargs.pop("n_tools")
        features_extractor_kwargs = {'n_tools': n_tools}
       #super(CApolicy, self).__init__(observation_space, action_space, lr_schedule, **kwargs, net_arch=None, features_extractor_class=NCA, features_extractor_kwargs=features_extractor_kwargs)
        super(CApolicy, self).__init__(observation_space, action_space, lr_schedule, **kwargs, net_arch=None, features_extractor_class=CA_0, features_extractor_kwargs=features_extractor_kwargs)
        # funky for CA type action
        use_sde = False
        dist_kwargs = None
        self.action_dist = make_proba_distribution(action_space, use_sde=use_sde, dist_kwargs=dist_kwargs)
        self._build(lr_schedule)
        self.action_net = IdentityActModule()
        self.value_net = IdentityValModule()


