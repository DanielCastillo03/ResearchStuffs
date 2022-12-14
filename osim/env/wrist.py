import math
import numpy as np
import os
from .utils.mygym import convert_to_gym
import gym
import opensim
import random
from .osim import OsimEnv


class WristEnv(OsimEnv):    
   model_path =   os.path.join(os.path.dirname(__file__), '../ARMS_Wrist_Hand_Model_3.3/Hand_Wrist_Model_for_development.osim')
   time_limit = 200
   targetX = 0
   targetY = 0
   
   def get_observation(self):
        state_desc = self.get_state_desc()

        res = [self.target_x, self.target_y]

        for joint in ["elbow","radioulnar",]:
            res += state_desc["joint_pos"][joint]
            res += state_desc["joint_vel"][joint]
            res += state_desc["joint_acc"][joint]

        for muscle in sorted(state_desc["muscles"].keys()):
            res += [state_desc["muscles"][muscle]["activation"]]

        res += state_desc["markers"]["thumb"]["pos"][:2]

        return res

   def get_observation_space_size(self):
        return 16 #46

   def generate_new_target(self):
        theta = random.uniform(math.pi*0, math.pi*2/3)
        radius = random.uniform(0.3, 0.65)
        self.target_x = math.cos(theta) * radius 
        self.target_y = -math.sin(theta) * radius + 0.8

        print('\ntarget: [{} {}]'.format(self.target_x, self.target_y))

        state = self.osim_model.get_state()

        self.target_joint.getCoordinate(1).setValue(state, self.target_x, False)

        self.target_joint.getCoordinate(2).setLocked(state, False)
        self.target_joint.getCoordinate(2).setValue(state, self.target_y, False)
        self.target_joint.getCoordinate(2).setLocked(state, True)
        self.osim_model.set_state(state)
        
   def reset(self, random_target=True, obs_as_dict=True):
        obs = super(WristEnv, self).reset(obs_as_dict=obs_as_dict)
        if random_target:
            self.generate_new_target()
        self.osim_model.reset_manager()
        return obs

   def __init__(self, *args, **kwargs):
        super(WristEnv, self).__init__(*args, **kwargs)
        blockos = opensim.Body('target', 0.0001 , opensim.Vec3(0), opensim.Inertia(1,1,.0001,0,0,0) );
        self.target_joint = opensim.PlanarJoint('target-joint',
                                  self.osim_model.model.getGround(), # PhysicalFrame
                                  opensim.Vec3(0, 0, 0),
                                  opensim.Vec3(0, 0, 0),
                                  blockos, # PhysicalFrame
                                  opensim.Vec3(0, 0, -0.25),
                                  opensim.Vec3(0, 0, 0))

        self.noutput = self.osim_model.noutput

        geometry = opensim.Ellipsoid(0.02, 0.02, 0.02);
        geometry.setColor(opensim.Green);
        blockos.attachGeometry(geometry)

        self.osim_model.model.addJoint(self.target_joint)
        self.osim_model.model.addBody(blockos)
        
        self.osim_model.model.initSystem()
    
   def reward(self):
        state_desc = self.get_state_desc()
        penalty = (state_desc["markers"]["thumb"]["pos"][0] - self.target_x)**2 + (state_desc["markers"]["thumb"]["pos"][1] - self.target_y)**2

        if np.isnan(penalty):
            penalty = 1
        return 1.-penalty

   def get_reward(self):
        return self.reward()


class WristVecEnv(WristEnv):
    def reset(self, obs_as_dict=False):
        obs = super(WristVecEnv, self).reset(obs_as_dict=obs_as_dict)
        if np.isnan(obs).any():
            obs = np.nan_to_num(obs)
        return obs
    def step(self, action, obs_as_dict=False):
        if np.isnan(action).any():
            action = np.nan_to_num(action)
        obs, reward, done, info = super(WristVecEnv, self).step(action, obs_as_dict=obs_as_dict)
        if np.isnan(obs).any():
            obs = np.nan_to_num(obs)
            done = True
            reward -10
        return obs, reward, done, info