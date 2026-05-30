import mujoco as mj
import numpy as np


class Controller:

    def __init__(self, m, d, xml_path, action, thigh_length, calf_length, hip_offset, ori_l=10, ori_theta=0.0):

        self.m = m
        self.d = d

        self.K = action[0]
        self.C = action[1]
        self.T_gain = action[2]

        self.thigh_length = thigh_length
        self.calf_length = calf_length
        self.hip_offset_full = hip_offset
        self.ori_l = ori_l
        self.ori_theta = ori_theta
        self.hip_left_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "hip_left")
        self.hip_right_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "hip_right")

        self.hip_left_dof = m.jnt_dofadr[self.hip_left_id]
        self.hip_right_dof = m.jnt_dofadr[self.hip_right_id]

        self.left_tip_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, "left_tip")
        self.right_tip_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, "right_tip")

        self.base_body_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "base")
    def cross2d(self, a, b):
        """
        2D scalar cross product
        """
        return a[0]*b[1] - a[1]*b[0]


    def perp(self, v):
        """
        [i] operator from paper
        [i][x y] = [-y x]
        """
        return np.array([-v[1], v[0]])

    def ee_pos(self):
        left = self.d.site_xpos[self.left_tip_id]
        right = self.d.site_xpos[self.right_tip_id]
        return 0.5 * (left + right)

    def base_pos(self):
        return self.d.xipos[self.base_body_id]

    def distance(self):
        return np.linalg.norm(self.ee_pos() - self.base_pos())

    def total_linear_force(self):

        l = self.distance()

        Jp = np.zeros((3, self.m.nv))
        mj.mj_jacSite(self.m, self.d, Jp, None, self.left_tip_id)

        vel = Jp @ self.d.qvel

        leg_vec = self.ee_pos() - self.base_pos()
        leg_dir = leg_vec / np.linalg.norm(leg_vec)

        ldot = leg_dir @ vel

        return self.K * (self.ori_l - l) - self.C * ldot


    def force_world(self):

        base = self.base_pos()
        ee = self.ee_pos()

        leg_vec = ee - base
        l = np.linalg.norm(leg_vec)

        leg_dir = leg_vec / l

        Fl = self.total_linear_force()
        F_lin = Fl * leg_dir
        alpha = np.arctan2(leg_dir[0], -leg_dir[2])
        tau_t = self.T_gain * (self.ori_theta - alpha)

        leg_perp = np.array([-leg_dir[2], 0.0, leg_dir[0]])
        F_tor = (tau_t / l) * leg_perp
        F = -F_lin - F_tor
        total_mass = float(np.sum(self.m.body_mass))
        F_grav = 0 * total_mass * self.m.opt.gravity
        return F + F_grav
    def get_ground_contact_forces(self):

        ground_id = mj.mj_name2id(self.m, mj.mjtObj.mjOBJ_GEOM, "floor")

        foot_left_id = mj.mj_name2id(self.m, mj.mjtObj.mjOBJ_GEOM, "foot_left")
        foot_right_id = mj.mj_name2id(self.m, mj.mjtObj.mjOBJ_GEOM, "foot_right")

        contact_list = []

        for i in range(self.d.ncon):

            con = self.d.contact[i]

            # check if this is ground contact
            if con.geom1 == ground_id or con.geom2 == ground_id:

                # check if the OTHER geom is one of the feet
                other_geom = con.geom2 if con.geom1 == ground_id else con.geom1

                if other_geom in [foot_left_id, foot_right_id]:

                    force = np.zeros(6)
                    mj.mj_contactForce(self.m, self.d, i, force)

                    contact_list.append((force[:3], con))

        return contact_list
    
    def analytical_jacobian(self):

        # ---------------------------------
        # BODY IDS
        # ---------------------------------

        left_hip_body = mj.mj_name2id(
            self.m, mj.mjtObj.mjOBJ_BODY, "l1_left"
        )

        right_hip_body = mj.mj_name2id(
            self.m, mj.mjtObj.mjOBJ_BODY, "l1_right"
        )

        left_knee_body = mj.mj_name2id(
            self.m, mj.mjtObj.mjOBJ_BODY, "l2_left"
        )

        right_knee_body = mj.mj_name2id(
            self.m, mj.mjtObj.mjOBJ_BODY, "l2_right"
        )

        # ---------------------------------
        # WORLD POSITIONS
        # ---------------------------------

        left_hip_3d = self.d.xpos[left_hip_body]
        right_hip_3d = self.d.xpos[right_hip_body]

        left_knee_3d = self.d.xpos[left_knee_body]
        right_knee_3d = self.d.xpos[right_knee_body]

        foot_3d = self.d.site_xpos[self.left_tip_id]

        # ---------------------------------
        # x-z plane -> 2D
        # ---------------------------------

        # PAPER CONSISTENT LABELING

        A0 = np.array([right_hip_3d[0], right_hip_3d[2]])
        B0 = np.array([left_hip_3d[0], left_hip_3d[2]])

        C = np.array([right_knee_3d[0], right_knee_3d[2]])
        D = np.array([left_knee_3d[0], left_knee_3d[2]])

        P = np.array([foot_3d[0], foot_3d[2]])

        # ---------------------------------
        # vectors
        # ---------------------------------

        r_AC = C - A0
        r_BD = D - B0

        r_DF = P - D
        r_CF = P - C

        r_CP = P - C

        # ---------------------------------
        # denominator
        # ---------------------------------

        denom = self.cross2d(r_DF, r_CF)

        if abs(denom) < 1e-8:
            denom = np.sign(denom) * 1e-8

        # ---------------------------------
        # J1
        # ---------------------------------

        J1_vec = (
            r_AC
            -
            (self.cross2d(r_DF, r_AC) / denom) * r_CP
        )

        J1 = self.perp(J1_vec)

        # ---------------------------------
        # J2
        # ---------------------------------

        J2 = (
            self.cross2d(r_DF, r_BD) / denom
        ) * self.perp(r_CP)

        # ---------------------------------
        # Assemble Jacobian
        # ---------------------------------

        J = np.column_stack((J1, J2))

        return J

    def joint_torque(self):

        Jp_left = np.zeros((3, self.m.nv))
        Jp_right = np.zeros((3, self.m.nv))

        # mj.mj_jacSite(self.m, self.d, Jp_left, None, self.left_tip_id)
        # mj.mj_jacSite(self.m, self.d, Jp_right, None, self.right_tip_id)
        Jp = 0.5 * (Jp_left + Jp_right)
        J = self.analytical_jacobian()
        print("J:", J)
        print("Jp:", Jp)
        F = self.force_world()
        F_planar = np.array([F[0], F[2]])
        #tau_full = Jp.T @ F
        tau = J.T @ F_planar
        # tau_left = tau_full[self.hip_left_dof]
        # tau_right = tau_full[self.hip_right_dof]
        tau_left = tau[1]
        tau_right = tau[0]
        return np.array([tau_left, tau_right])