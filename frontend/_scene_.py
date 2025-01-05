# File: _scene_.py
# Author: Ryoichi Ando (ryoichi.ando@zozo.com)
# License: Apache v2.0

import numpy as np
import pandas as pd
from tqdm import tqdm
import shutil
import os
import colorsys
from typing import Optional
from ._plot_ import PlotManager, Plot
from ._asset_ import AssetManager
from dataclasses import dataclass

EPS = 1e-3


class SceneManager:
    """SceneManager class. Use this to manage scenes."""

    def __init__(self, plot: PlotManager, asset: AssetManager, save_func):
        """Initialize the scene manager."""
        self._plot = plot
        self._asset = asset
        self._scene: dict[str, Scene] = {}
        self._save_func = save_func

    def create(self, name: str) -> "Scene":
        """Create a new scene.

        Create a scene only if the name does not exist. Raise an exception if the name already exists.

        Args:
            name (str): The name of the scene to create.

        Returns:
            Scene: The created scene.
        """
        if name in self._scene.keys():
            raise Exception(f"scene {name} already exists")
        else:
            scene = Scene(name, self._plot, self._asset, self._save_func)
            self._scene[name] = scene
            return scene

    def select(self, name: str, create: bool = True) -> "Scene":
        """Select a scene.

        If the scene exists, it will be selected. If it does not exist and create is True, a new scene will be created.

        Args:
            name (str): The name of the scene to select.
            create (bool, optional): Whether to create a new scene if it does not exist. Defaults to True.
        """
        if create and name not in self._scene.keys():
            return self.create(name)
        else:
            return self._scene[name]

    def remove(self, name: str):
        """Remove a scene from the manager.

        Args:
            name (str): The name of the scene to remove.
        """
        if name in self._scene.keys():
            del self._scene[name]

    def clear(self):
        """Clear all the scenes in the manager."""
        self._scene = {}

    def list(self) -> list[str]:
        """List all the scenes in the manager.

        Returns:
            list[str]: A list of scene names.
        """
        return list(self._scene.keys())


class Wall:
    """An invisible wall class."""

    def __init__(self):
        """Initialize the wall."""
        self._normal = [0, 1, 0]
        self._entry = []
        self._transition = "smooth"

    def get_entry(self) -> list[tuple[list[float], float]]:
        """Get a list of time-dependent wall entries.

        Returns:
            list[tuple[list[float], float]]: A list of time-dependent entries, each containing a position and time.
        """
        return self._entry

    def add(self, pos: list[float], normal: list[float]) -> "Wall":
        """Add an invisible wall information.

        Args:
            pos (list[float]): The position of the wall.
            normal (list[float]): The outer normal of the wall.

        Returns:
            Wall: The invisible wall.
        """
        if len(self._entry):
            raise Exception("wall already exists")
        else:
            self._normal = normal
            self._entry.append((pos, 0.0))
            return self

    def _check_time(self, time: float):
        """Check if the time is valid.

        Args:
            time (float): The time to check.
        """
        if time <= self._entry[-1][1]:
            raise Exception("time must be greater than the last time")

    def move_to(self, pos: list[float], time: float) -> "Wall":
        """Move the wall to a new position at a specific time.

        Args:
            pos (list[float]): The target position of the wall.
            time (float): The absolute time to move the wall.

        Returns:
            Wall: The invisible wall.
        """
        self._check_time(time)
        self._entry.append((pos, time))
        return self

    def move_by(self, delta: list[float], time: float) -> "Wall":
        """Move the wall by a positional delta at a specific time.

        Args:
            delta (list[float]): The positional delta to move the wall.
            time (float): The absolute time to move the wall.

        Returns
            Wall: The invisible wall.
        """
        self._check_time(time)
        pos = self._entry[-1][0] + delta
        self._entry.append((pos, time))
        return self

    def interp(self, transition: str) -> "Wall":
        """Set the transition type for the wall."""
        self._transition = transition
        return self


class Sphere:
    """An invisible sphere class."""

    def __init__(self):
        """Initialize the sphere."""
        self._entry = []
        self._hemisphere = False
        self._invert = False
        self._transition = "smooth"

    def hemisphere(self) -> "Sphere":
        """Turn the sphere into a hemisphere, so the half of the sphere top becomes empty, like a bowl."""
        self._hemisphere = True
        return self

    def invert(self) -> "Sphere":
        """Invert the sphere, so the inside becomes empty and the outside becomes solid."""
        self._invert = True
        return self

    def interp(self, transition: str) -> "Sphere":
        """Set the transition type for the sphere."""
        self._transition = transition
        return self

    def get_entry(self) -> list[tuple[list[float], float, float]]:
        """Get the time-dependent sphere entries."""
        return self._entry

    def add(self, pos: list[float], radius: float) -> "Sphere":
        """Add an invisible sphere information.

        Args:
            pos (list[float]): The position of the sphere.
            radius (float): The radius of the sphere.

        Returns:
            Sphere: The sphere.
        """
        if len(self._entry):
            raise Exception("sphere already exists")
        else:
            self._entry.append((pos, radius, 0.0))
            return self

    def _check_time(self, time: float):
        """Check if the time is valid.

        Args:
            time (float): The time to check.
        """
        if time <= self._entry[-1][2]:
            raise Exception(
                "time must be greater than the last time. last time is %f"
                % self._entry[-1][2]
            )

    def transform_to(self, pos: list[float], radius: float, time: float) -> "Sphere":
        """Change the sphere to a new position and radius at a specific time.

        Args:
            pos (list[float]): The target position of the sphere.
            radius (float): The target radius of the sphere.
            time (float): The absolute time to transform the sphere.

        Returns:
            Spere: The sphere.
        """
        self._check_time(time)
        self._entry.append((pos, radius, time))
        return self

    def move_to(self, pos: list[float], time: float) -> "Sphere":
        """Move the sphere to a new position at a specific time.

        Args:
            pos list[float]: The target position of the sphere.
            time (float): The absolute time to move the sphere.

        Returns:
            Sphere: The sphere.
        """
        self._check_time(time)
        radius = self._entry[-1][1]
        self._entry.append((pos, radius, time))
        return self

    def move_by(self, delta: list[float], time: float) -> "Sphere":
        """Move the sphere by a positional delta at a specific time.

        Args:
            delta (list[float]): The positional delta to move the sphere.
            time (float): The absolute time to move the sphere.

        Returns:
            Sphere: The sphere.
        """
        self._check_time(time)
        pos = self._entry[-1][0] + delta
        radius = self._entry[-1][1]
        self._entry.append((pos, radius, time))
        return self

    def radius(self, radius: float, time: float) -> "Sphere":
        """Change the radius of the sphere at a specific time.

        Args:
            radius (float): The target radius of the sphere.
            time (float): The absolute time to change the radius.

        Returns:
            Sphere: The sphere.
        """
        self._check_time(time)
        pos = self._entry[-1][0]
        self._entry.append((pos, radius, time))
        return self


@dataclass
class SpinData:
    """Represents spinning data for a set of vertices."""

    center: np.ndarray
    axis: np.ndarray
    angular_velocity: float
    t_start: float
    t_end: float


@dataclass
class PinKeyframe:
    """Represents a single keyframe for pinned vertices."""

    position: np.ndarray
    time: float


@dataclass
class PinData:
    """Represents pinning data for a set of vertices."""

    index: list[int]
    keyframe: list[PinKeyframe]
    spin: list[SpinData]
    should_unpin: bool = False
    transition: str = "smooth"
    pull_strength: float = 0.0


class PinHolder:
    """Class to manage pinning behavior of objects."""

    def __init__(self, obj: "Object", indices: list[int]):
        """Initialize pin object.

        Args:
            obj (Object): The object to pin.
            indices (list[int]): The indices of the vertices to pin.
        """
        self._obj = obj
        self._data = PinData(
            index=indices,
            spin=[],
            keyframe=[],
        )

    def set_pull(self, strength: float) -> "PinHolder":
        """Set pull strength for pinned vertices.

        Args:
            strength (float): The pull strength.

        Returns:
            PinHolder: The pinholder with the updated pull strength.
        """
        self._data.pull_strength = strength
        return self

    def interp(self, transition: str) -> "PinHolder":
        """Set the transition type for the pinning.

        Args:
            transition (str): The transition type. Currently supported: "smooth", "linear". Default is "smooth".

        Returns:
            PinHolder: The pinholder with the updated transition type.
        """
        self._data.transition = transition
        return self

    def unpin(self) -> "PinHolder":
        """Unpin the object.

        Returns:
            PinHolder: The pinholder with the unpinned vertices.
        """
        self._data.should_unpin = True
        return self

    def move_by(self, delta_pos, time: float) -> "PinHolder":
        """Move the object by a positional delta over a specified time.

        Args:
            delta_pos (list[float]): The positional delta.
            time (float): The time over which to move the object.

        Returns:
            PinHolder: The pinholder with the updated position.
        """
        delta_pos = np.array(delta_pos).reshape((-1, 3))
        if not self._data.keyframe:
            target = self._obj.vertex()[self._data.index] + delta_pos
        else:
            target = self._data.keyframe[-1].position + delta_pos
        return self.move_to(target, time)

    def hold(self, time: float) -> "PinHolder":
        """Hold the object in its current position for a specified time.

        Args:
            time (float): The time to hold the object.

        Returns:
            PinHolder: The pinholder with the held position.
        """
        return self.move_by([0, 0, 0], time)

    def move_to(
        self,
        target: np.ndarray,
        time: float,
    ) -> "PinHolder":
        """Move the object to a target position at a specified time.

        Args:
            target (np.ndarray): The target position.
            time (float): The absolute time over which to move the object.

        Returns:
            PinHolder: The pinholder with the updated position.
        """
        if len(target) != len(self.index):
            raise Exception("target must have the same length as pin")
        elif time == 0:
            raise Exception("time must be greater than zero")

        if not self.keyframe:
            self._add_movement(self._obj.vertex()[self.index], 0)

        self._add_movement(target, time)
        return self

    def _add_movement(self, target_pos: np.ndarray, time: float):
        final_time = self._data.keyframe[-1].time if self._data.keyframe else None
        if final_time is not None and time <= final_time:
            raise Exception("time must be greater than the last time")
        self._data.keyframe.append(PinKeyframe(target_pos, time))

    def spin(
        self,
        center: list[float] = [0.0, 0.0, 0.0],
        axis: list[float] = [0.0, 1.0, 0.0],
        angular_velocity: float = 360.0,
        t_start: float = 0.0,
        t_end: float = float("inf"),
    ) -> "PinHolder":
        self._data.spin.append(
            SpinData(np.array(center), np.array(axis), angular_velocity, t_start, t_end)
        )
        return self

    @property
    def data(self) -> Optional[PinData]:
        """Get the pinning data.

        Returns:
            PinData: The pinning data.
        """
        return self._data

    @property
    def index(self) -> list[int]:
        """Get pinned vertex indices."""
        return self._data.index

    @property
    def spinner(self) -> list[SpinData]:
        """Get list of spins."""
        return self._data.spin

    @property
    def keyframe(self) -> list[PinKeyframe]:
        """Get list of movement keyframes."""
        return self._data.keyframe

    @property
    def should_unpin(self) -> bool:
        """Check if vertices should unpin after movement."""
        return self._data.should_unpin

    @property
    def pull_strength(self) -> float:
        """Get pull force strength."""
        return self._data.pull_strength

    @property
    def transition(self) -> str:
        """Get the transition type."""
        return self._data.transition


class FixedScene:
    """A fixed scene class."""

    def __init__(
        self,
        plot: PlotManager,
        name: str,
        vert: np.ndarray,
        color: np.ndarray,
        vel: np.ndarray,
        uv: np.ndarray,
        rod: np.ndarray,
        tri: np.ndarray,
        tet: np.ndarray,
        wall: list[Wall],
        sphere: list[Sphere],
        rod_vert_range: tuple[int, int],
        shell_vert_range: tuple[int, int],
        rod_count: int,
        shell_count: int,
    ):
        """Initialize the fixed scene.

        Args:
            plot (PlotManager): The plot manager.
            name (str): The name of the scene.
            vert (np.ndarray): The vertices of the scene.
            color (np.ndarray): The colors of the vertices.
            vel (np.ndarray): The velocities of the vertices.
            uv (np.ndarray): The UV coordinates of the vertices.
            rod (np.ndarray): The rod elements.
            tri (np.ndarray): The triangle elements.
            tet (np.ndarray): The tetrahedral elements.
            wall (list[Wall]): The invisible walls.
            sphere (list[Sphere]): The invisible spheres.
            rod_vert_range (tuple[int, int]): The index range of the rod vertices.
            shell_vert_range (tuple[int, int]): The index range of the shell vertices.
            rod_count (int): The number of rod elements.
            shell_count (int): The number of shell elements.
        """

        self._plot = plot
        self._name = name
        self._vert = vert
        self._color = color
        self._vel = vel
        self._uv = uv
        self._rod = rod
        self._tri = tri
        self._tet = tet
        self._pin: list[PinData] = []
        self._spin: list[SpinData] = []
        self._static_vert = np.zeros(0)
        self._static_color = np.zeros(0)
        self._static_tri = np.zeros(0)
        self._stitch_ind = np.zeros(0)
        self._stitch_w = np.zeros(0)
        self._wall = wall
        self._sphere = sphere
        self._rod_vert_range = rod_vert_range
        self._shell_vert_range = shell_vert_range
        self._rod_count = rod_count
        self._shell_count = shell_count

    def report(self) -> "FixedScene":
        """Print a summary of the scene."""
        data = {}
        data["#vert"] = len(self._vert)
        if len(self._rod):
            data["#rod"] = len(self._rod)
        if len(self._tri):
            data["#tri"] = len(self._tri)
        if len(self._tet):
            data["#tet"] = len(self._tet)
        if len(self._pin):
            data["#pin"] = sum([len(pin.index) for pin in self._pin])
        if len(self._static_vert) and len(self._static_tri):
            data["#static_vert"] = len(self._static_vert)
            data["#static_tri"] = len(self._static_tri)
        if len(self._stitch_ind) and len(self._stitch_w):
            data["#stitch_ind"] = len(self._stitch_ind)
        for key, value in data.items():
            if isinstance(value, int):
                data[key] = [f"{value:,}"]
            elif isinstance(value, float):
                data[key] = [f"{value:.2e}"]
            else:
                data[key] = [str(value)]

        from IPython.display import display, HTML

        if self._plot.is_jupyter_notebook():
            df = pd.DataFrame(data)
            html = df.to_html(classes="table", index=False)
            display(HTML(html))
        else:
            print(data)
        return self

    def export(
        self, vert: np.ndarray, path: str, include_static: bool = True
    ) -> "FixedScene":
        """Export the scene to a mesh file.

        Export the scene to a mesh file. The vertices must be explicitly provided.

        Args:
            vert (np.ndarray): The vertices of the scene.
            path (str): The path to the mesh file. Supported formats are `.ply`, `.obj`
            include_static (bool, optional): Whether to include the static mesh. Defaults to True.

        Returns:
            FixedScene: The fixed scene.
        """

        import open3d as o3d

        o3d_mesh = o3d.geometry.TriangleMesh(
            o3d.utility.Vector3dVector(vert),
            o3d.utility.Vector3iVector(self._tri),
        )
        o3d_mesh.vertex_colors = o3d.utility.Vector3dVector(self._color)

        if include_static and len(self._static_vert) and len(self._static_tri):
            o3d_static = o3d.geometry.TriangleMesh(
                o3d.utility.Vector3dVector(self._static_vert),
                o3d.utility.Vector3iVector(self._static_tri),
            )
            o3d_static.vertex_colors = o3d.utility.Vector3dVector(self._static_color)
            o3d_mesh += o3d_static

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        o3d.io.write_triangle_mesh(path, o3d_mesh)
        return self

    def export_fixed(self, path: str, delete_exist: bool) -> "FixedScene":
        """Export the fixed scene as a simulatio-readible format.

        Args:
            path (str): The path to the output directory.
            delete_exist (bool): Whether to delete the existing directory.

        Returns:
            FixedScene: The fixed scene.
        """
        if os.path.exists(path):
            if delete_exist:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            else:
                raise Exception(f"file {path} already exists")
        else:
            os.makedirs(path)
        info_path = os.path.join(path, "info.toml")
        with open(info_path, "w") as f:
            f.write("[count]\n")
            f.write(f"vert = {len(self._vert)}\n")
            f.write(f"rod = {len(self._rod)}\n")
            f.write(f"tri = {len(self._tri)}\n")
            f.write(f"tet = {len(self._tet)}\n")
            f.write(f"static_vert = {len(self._static_vert)}\n")
            f.write(f"static_tri = {len(self._static_tri)}\n")
            f.write(f"pin_block = {len(self._pin)}\n")
            f.write(f"wall = {len(self._wall)}\n")
            f.write(f"sphere = {len(self._sphere)}\n")
            f.write(f"stitch = {len(self._stitch_ind)}\n")
            f.write(f"rod_vert_start = {self._rod_vert_range[0]}\n")
            f.write(f"rod_vert_end = {self._rod_vert_range[1]}\n")
            f.write(f"shell_vert_start = {self._shell_vert_range[0]}\n")
            f.write(f"shell_vert_end = {self._shell_vert_range[1]}\n")
            f.write(f"rod_count = {self._rod_count}\n")
            f.write(f"shell_count = {self._shell_count}\n")
            f.write("\n")

            for i, pin in enumerate(self._pin):
                f.write(f"[pin-{i}]\n")
                f.write(f"keyframe = {len(pin.keyframe)}\n")
                f.write(f"spin = {len(pin.spin)}\n")
                f.write(f"pin = {len(pin.index)}\n")
                f.write(f"pull = {float(pin.pull_strength)}\n")
                f.write(f"unpin = {'true' if pin.should_unpin else 'false'}\n")
                f.write(f'transition = "{pin.transition}"\n')

            for i, wall in enumerate(self._wall):
                normal = wall._normal
                f.write(f"[wall-{i}]\n")
                f.write(f"keyframe = {len(wall._entry)}\n")
                f.write(f"nx = {float(normal[0])}\n")
                f.write(f"ny = {float(normal[1])}\n")
                f.write(f"nz = {float(normal[2])}\n")
                f.write(f'transition = "{wall._transition}"\n')
                f.write("\n")

            for i, sphere in enumerate(self._sphere):
                f.write(f"[sphere-{i}]\n")
                f.write(f"keyframe = {len(sphere._entry)}\n")
                f.write(f"hemisphere = {'true' if sphere._hemisphere else 'false'}\n")
                f.write(f"invert = {'true' if sphere._invert else 'false'}\n")
                f.write(f'transition = "{sphere._transition}"\n')
                f.write("\n")

        bin_path = os.path.join(path, "bin")
        os.makedirs(bin_path)

        self._vert.astype(np.float32).tofile(os.path.join(bin_path, "vert.bin"))
        self._color.astype(np.float32).tofile(os.path.join(bin_path, "color.bin"))
        self._vel.astype(np.float32).tofile(os.path.join(bin_path, "vel.bin"))
        if np.linalg.norm(self._uv) > 0:
            self._uv.astype(np.float32).tofile(os.path.join(bin_path, "uv.bin"))

        if len(self._rod):
            self._rod.astype(np.uint64).tofile(os.path.join(bin_path, "rod.bin"))
        if len(self._tri):
            self._tri.astype(np.uint64).tofile(os.path.join(bin_path, "tri.bin"))
        if len(self._tet):
            self._tet.astype(np.uint64).tofile(os.path.join(bin_path, "tet.bin"))
        if len(self._static_vert):
            self._static_vert.astype(np.float32).tofile(
                os.path.join(bin_path, "static_vert.bin")
            )
            self._static_tri.astype(np.uint64).tofile(
                os.path.join(bin_path, "static_tri.bin")
            )
            self._static_color.astype(np.float32).tofile(
                os.path.join(bin_path, "static_color.bin")
            )
        if len(self._stitch_ind) and len(self._stitch_w):
            self._stitch_ind.astype(np.uint64).tofile(
                os.path.join(bin_path, "stitch_ind.bin")
            )
            self._stitch_w.astype(np.float32).tofile(
                os.path.join(bin_path, "stitch_w.bin")
            )
        for i, pin in enumerate(self._pin):
            with open(os.path.join(bin_path, f"pin-ind-{i}.bin"), "wb") as f:
                np.array(pin.index, dtype=np.uint64).tofile(f)
            if len(pin.keyframe):
                target_dir = os.path.join(bin_path, f"pin-{i}")
                os.makedirs(target_dir)
                with open(os.path.join(bin_path, f"pin-timing-{i}.bin"), "wb") as f:
                    time_array = [entry.time for entry in pin.keyframe]
                    np.array(time_array, dtype=np.float32).tofile(f)
                for j, entry in enumerate(pin.keyframe):
                    with open(os.path.join(target_dir, f"{j}.bin"), "wb") as f:
                        np.array(entry.position, dtype=np.float32).tofile(f)
            if len(pin.spin):
                spin_dir = os.path.join(path, "spin")
                os.makedirs(spin_dir, exist_ok=True)
                with open(os.path.join(spin_dir, f"spin-{i}.toml"), "w") as f:
                    for j, spin in enumerate(pin.spin):
                        f.write(f"[spin-{j}]\n")
                        f.write(f"center_x = {float(spin.center[0])}\n")
                        f.write(f"center_y = {float(spin.center[1])}\n")
                        f.write(f"center_z = {float(spin.center[2])}\n")
                        f.write(f"axis_x = {float(spin.axis[0])}\n")
                        f.write(f"axis_y = {float(spin.axis[1])}\n")
                        f.write(f"axis_z = {float(spin.axis[2])}\n")
                        f.write(f"angular_velocity = {float(spin.angular_velocity)}\n")
                        f.write(f"t_start = {float(spin.t_start)}\n")
                        f.write(f"t_end = {float(spin.t_end)}\n")

        for i, wall in enumerate(self._wall):
            with open(os.path.join(bin_path, f"wall-pos-{i}.bin"), "wb") as f:
                pos = np.array(
                    [p for pos, _ in wall._entry for p in pos], dtype=np.float32
                )
                pos.tofile(f)
            with open(os.path.join(bin_path, f"wall-timing-{i}.bin"), "wb") as f:
                timing = np.array([t for _, t in wall._entry], dtype=np.float32)
                timing.tofile(f)

        for i, sphere in enumerate(self._sphere):
            with open(os.path.join(bin_path, f"sphere-pos-{i}.bin"), "wb") as f:
                pos = np.array(
                    [p for pos, _, _ in sphere._entry for p in pos], dtype=np.float32
                )
                pos.tofile(f)
            with open(os.path.join(bin_path, f"sphere-radius-{i}.bin"), "wb") as f:
                radius = np.array([r for _, r, _ in sphere._entry], dtype=np.float32)
                radius.tofile(f)
            with open(os.path.join(bin_path, f"sphere-timing-{i}.bin"), "wb") as f:
                timing = np.array([t for _, _, t in sphere._entry], dtype=np.float32)
                timing.tofile(f)

        return self

    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        """Compute the bounding box of the scene.

        Returns:
            tuple[np.ndarray, np.ndarray]: The maximum and minimum coordinates of the bounding box.
        """
        vert = self._vert
        return (np.max(vert, axis=0), np.min(vert, axis=0))

    def center(self) -> np.ndarray:
        """Compute the area-weighted center of the scene.

        Returns:
            np.ndarray: The area-weighted center of the scene.
        """
        vert = self._vert
        tri = self._tri
        center = np.zeros(3)
        area_sum = 0
        for f in tri:
            a, b, c = vert[f[0]], vert[f[1]], vert[f[2]]
            area = 0.5 * np.linalg.norm(np.cross(b - a, c - a))
            center += area * (a + b + c) / 3
            area_sum += area
        if area_sum == 0:
            raise Exception("no area")
        else:
            return center / area_sum

    def _average_tri_area(self) -> float:
        """Compute the average triangle area of the scene.

        Returns:
            float: The average triangle area of the scene.
        """
        vert = self._vert
        tri = self._tri
        area = 0.0
        if len(tri):
            for f in tri:
                a, b, c = vert[f[0]], vert[f[1]], vert[f[2]]
                area += 0.5 * float(np.linalg.norm(np.cross(b - a, c - a)))
            return area / len(tri)
        else:
            return 0.0

    def set_pin(self, pin: list[PinData]):
        """Set the pinning data of all the objects.

        Args:
            pin_data (list[PinData]): A list of pinning data.
        """
        self._pin = pin

    def set_spin(self, spin: list[SpinData]):
        """Set the spinning data of all the objects.

        Args:
            spin_data (list[SpinData]): A list of spinning data.
        """
        self._spin = spin

    def set_static(self, vert: np.ndarray, tri: np.ndarray, color: np.ndarray):
        """Set the static mesh data.

        Args:
            vert (np.ndarray): The vertices of the static mesh.
            tri (np.ndarray): The triangle elements of the static mesh.
            color (np.ndarray): The colors of the static mesh.
        """
        self._static_vert = vert
        self._static_tri = tri
        self._static_color = color

    def set_stitch(self, ind: np.ndarray, w: np.ndarray):
        """Set the stitch data.

        Args:
            ind (np.ndarray): The stitch indices.
            w (np.ndarray): The stitch weights.
        """
        self._stitch_ind = ind
        self._stitch_w = w

    def time(self, time: float) -> np.ndarray:
        """Compute the vertex positions at a specific time.

        Args:
            time (float): The time to compute the vertex positions.

        Returns:
            np.ndarray: The vertex positions at the specified time.
        """
        vert = self._vert.copy()
        for pin in self._pin:
            last_time = pin.keyframe[-1].time if len(pin.keyframe) else 0.0
            last_position = (
                pin.keyframe[-1].position if len(pin.keyframe) else vert[pin.index]
            )
            for i, entry in enumerate(pin.keyframe):
                next_entry = pin.keyframe[i + 1] if i + 1 < len(pin.keyframe) else None
                if entry.time >= last_time:
                    vert[pin.index] = last_position
                    break
                elif next_entry is not None:
                    if time >= entry.time and time < next_entry.time:
                        t1, t2 = entry.time, next_entry.time
                        q1, q2 = entry.position, next_entry.position
                        r = (time - t1) / (t2 - t1)
                        if pin.transition == "smooth":
                            r = r * r * (3.0 - 2.0 * r)
                        vert[pin.index] = q1 * (1 - r) + q2 * r
                        break
            for p in pin.spin:
                t = min(time, p.t_end) - p.t_start
                radian_velocity = p.angular_velocity / 180.0 * np.pi
                angle = radian_velocity * t
                axis = p.axis / np.linalg.norm(p.axis)

                # Rodrigues rotation formula
                cos_theta = np.cos(angle)
                sin_theta = np.sin(angle)
                points = vert[pin.index] - p.center
                rotated = (
                    points * cos_theta
                    + np.cross(axis, points) * sin_theta
                    + np.outer(np.dot(points, axis), axis) * (1.0 - cos_theta)
                )
                vert[pin.index] = rotated + p.center
        vert += time * self._vel
        return vert

    def check_intersection(self) -> "FixedScene":
        """Check for self-intersections and intersections with the static mesh.

        Returns:
            FixedScene: The fixed scene.
        """
        import open3d as o3d

        if len(self._vert) and len(self._tri):
            o3d_mesh = o3d.geometry.TriangleMesh(
                o3d.utility.Vector3dVector(self._vert),
                o3d.utility.Vector3iVector(self._tri),
            )
            if o3d_mesh.is_self_intersecting():
                print("WARNING: mesh is self-intersecting")
            if len(self._static_vert) and len(self._static_tri):
                o3d_static = o3d.geometry.TriangleMesh(
                    o3d.utility.Vector3dVector(self._static_vert),
                    o3d.utility.Vector3iVector(self._static_tri),
                )
                if o3d_static.is_self_intersecting():
                    print("WARNING: static mesh is self-intersecting")
                if o3d_static.is_intersecting(o3d_mesh):
                    print("WARNING: mesh is intersecting with static mesh")
        return self

    def preview(
        self,
        vert: Optional[np.ndarray] = None,
        shading: dict = {},
        show_stitch: bool = True,
        show_pin: bool = True,
    ) -> Optional["Plot"]:
        """Preview the scene.

        Args:
            vert (Optional[np.ndarray], optional): The vertices to preview. Defaults to None.
            shading (dict, optional): The shading options. Defaults to {}.
            show_stitch (bool, optional): Whether to show the stitch. Defaults to True.
            show_pin (bool, optional): Whether to show the pin. Defaults to True.

        Returns:
            Optional[Plot]: The plot object if in a Jupyter notebook, otherwise None.
        """
        if self._plot.is_jupyter_notebook():
            if vert is None:
                vert = self._vert
            color = self._color
            plot = None

            if len(self._tri):
                if plot is None:
                    plot = self._plot.create().tri(
                        vert, self._tri, color=color, shading=shading
                    )
                else:
                    plot.add.tri(vert, self._tri, color)

            if len(self._static_vert):
                if plot is None:
                    plot = self._plot.create().tri(
                        self._static_vert,
                        self._static_tri,
                        color=self._static_color,
                    )
                else:
                    plot.add.tri(
                        self._static_vert,
                        self._static_tri,
                        self._static_color,
                    )

            if len(self._rod):
                if plot is None:
                    plot = self._plot.create().curve(vert, self._rod, shading=shading)
                else:
                    plot.add.edge(vert, self._rod)

            if plot is not None:
                if show_stitch and len(self._stitch_ind) and len(self._stitch_w):
                    stitch_vert, stitch_edge = [], []
                    for ind, w in zip(self._stitch_ind, self._stitch_w):
                        x0, y0, y1 = vert[ind[0]], vert[ind[1]], vert[ind[2]]
                        w0, w1 = w[0], w[1]
                        idx0, idx1 = len(stitch_vert), len(stitch_vert) + 1
                        stitch_vert.append(x0)
                        stitch_vert.append(w0 * y0 + w1 * y1)
                        stitch_edge.append([idx0, idx1])
                    stitch_vert = np.array(stitch_vert)
                    stitch_edge = np.array(stitch_edge)
                    if plot._darkmode:
                        color = np.array([1, 1, 1])
                    else:
                        color = np.array([0, 0, 0])
                    plot.add.edge(stitch_vert, stitch_edge)

                has_vel = np.linalg.norm(self._vel) > 0
                if show_pin and (self._pin or has_vel):
                    max_time = 0
                    if self._pin:
                        avg_area = self._average_tri_area()
                        avg_length = np.sqrt(avg_area)
                        shading["point_size"] = 5 * avg_length
                        pin_verts = np.vstack([vert[pin.index] for pin in self._pin])
                        plot.add.point(pin_verts)
                        max_time = max(
                            [
                                pin.keyframe[-1].time if len(pin.keyframe) else 0
                                for pin in self._pin
                            ]
                        )
                        for p in self._pin:
                            for spin in p.spin:
                                if spin.t_end == float("inf"):
                                    max_time = max(max_time, 1.0)
                                else:
                                    max_time = max(max_time, spin.t_end)
                    if has_vel:
                        max_time = max(max_time, 1.0)
                    if max_time > 0:

                        def update(time=0):
                            nonlocal plot
                            vert = self.time(time)
                            if plot is not None:
                                plot.update(vert)

                        from ipywidgets import interact

                        interact(update, time=(0, max_time, 0.01))
                return plot
            else:
                raise Exception("no plot")
        else:
            return None


class SceneInfo:
    def __init__(self, name: str, scene: "Scene"):
        self._scene = scene
        self.name = name


class InvisibleAdder:
    def __init__(self, scene: "Scene"):
        self._scene = scene

    def sphere(self, position: list[float], radius: float) -> Sphere:
        """Add an invisible sphere to the scene.

        Args:
            position (list[float]): The position of the sphere.
            radius (float): The radius of the sphere.
        Returns:
            Sphere: The invisible sphere.
        """
        sphere = Sphere().add(position, radius)
        self._scene._sphere.append(sphere)
        return sphere

    def wall(self, position: list[float], normal: list[float]) -> Wall:
        """Add an invisible wall to the scene.

        Args:
            position (list[float]): The position of the wall.
            normal (list[float]): The outer normal of the wall.
        Returns:
            Wall: The invisible wall.
        """
        wall = Wall().add(position, normal)
        self._scene._wall.append(wall)
        return wall


class ObjectAdder:
    def __init__(self, scene: "Scene"):
        self._scene = scene
        self.invisible = InvisibleAdder(
            scene
        )  #: InvisibleAdder: The invisible object adder.

    def __call__(self, mesh_name: str, ref_name: str = "") -> "Object":
        """Add a mesh to the scene.

        Args:
            mesh_name (str): The name of the mesh to add.
            ref_name (str, optional): The reference name of the object.

        Returns:
            Object: The added object.
        """
        if ref_name == "":
            ref_name = mesh_name
            count = 0
            while ref_name in self._scene._object.keys():
                count += 1
                ref_name = f"{mesh_name}_{count}"
        mesh_list = self._scene._asset.list()
        if mesh_name not in mesh_list:
            raise Exception(f"mesh_name '{mesh_name}' does not exist")
        elif ref_name in self._scene._object.keys():
            raise Exception(f"ref_name '{ref_name}' already exists")
        else:
            obj = Object(self._scene._asset, mesh_name)
            self._scene._object[ref_name] = obj
            return obj


class Scene:
    """A scene class."""

    def __init__(self, name: str, plot: PlotManager, asset: AssetManager, save_func):
        self._name = name
        self._plot = plot
        self._asset = asset
        self._save_func = save_func
        self._object: dict[str, Object] = {}
        self._sphere: list[Sphere] = []
        self._wall: list[Wall] = []
        self.add = ObjectAdder(self)  #: ObjectAdder: The object adder.
        self.info = SceneInfo(name, self)  #: SceneInfo: The scene information.

    def clear(self) -> "Scene":
        """Clear all objects from the scene.

        Returns:
            Scene: The cle  ared scene.
        """
        self._object.clear()
        return self

    def pick(self, name: str) -> "Object":
        if name not in self._object.keys():
            raise Exception(f"object {name} does not exist")
        else:
            return self._object[name]

    def build(self) -> FixedScene:
        """Build the fixed scene from the current scene.

        Returns:
            FixedScene: The built fixed scene.
        """
        pbar = tqdm(total=10, desc="build", ncols=70)
        for _, obj in self._object.items():
            obj.update_static()

        concat_count = 0
        dyn_objects = [
            obj for obj in self._object.values() if not obj.static and not obj._color
        ]
        n = len(dyn_objects)
        for i, obj in enumerate(dyn_objects):
            r, g, b = colorsys.hsv_to_rgb(i / n, 0.75, 1.0)
            obj.default_color(r, g, b)

        def add_entry(
            map,
            entry,
        ):
            nonlocal concat_count
            for e in entry:
                for vi in e:
                    if map[vi] == -1:
                        map[vi] = concat_count
                        concat_count += 1

        tag = {}
        for name, obj in self._object.items():
            assert name not in tag
            if not obj.static:
                vert = obj.get("V")
                if vert is not None:
                    tag[name] = [-1] * len(vert)

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static and obj.get("T") is None:
                map = tag[name]
                vert, edge = obj.get("V"), obj.get("E")
                if vert is not None and edge is not None:
                    add_entry(
                        map,
                        edge,
                    )
        rod_vert_start, rod_vert_end = 0, concat_count

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static and obj.get("T") is None:
                map = tag[name]
                vert, tri = obj.get("V"), obj.get("F")
                if vert is not None and tri is not None:
                    add_entry(
                        map,
                        tri,
                    )
        shell_vert_start, shell_vert_end = rod_vert_end, concat_count

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static:
                vert = obj.get("V")
                if vert is not None:
                    map = tag[name]
                    for i in range(len(vert)):
                        if map[i] == -1:
                            map[i] = concat_count
                            concat_count += 1

        concat_vert = np.zeros((concat_count, 3))
        concat_color = np.zeros((concat_count, 3))
        concat_vel = np.zeros((concat_count, 3))
        concat_uv = np.zeros((concat_count, 2))
        concat_pin = []
        concat_rod = []
        concat_tri = []
        concat_tet = []
        concat_static_vert = []
        concat_static_tri = []
        concat_static_color = []
        concat_stitch_ind = []
        concat_stitch_w = []

        def vec_map(map, elm):
            result = elm.copy()
            for i in range(len(elm)):
                result[i] = [map[vi] for vi in elm[i]]
            return result

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static:
                map = tag[name]
                vert, uv = obj.vertex(), obj._uv
                if vert is not None:
                    concat_vert[map] = vert
                    concat_vel[map] = obj._velocity
                    concat_color[map] = obj.get("color")
                if uv is not None:
                    concat_uv[map] = uv

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static:
                map = tag[name]
                edge = obj.get("E")
                if edge is not None and obj.get("T") is None:
                    concat_rod.extend(vec_map(map, edge))
        rod_count = len(concat_rod)

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static:
                map = tag[name]
                tri = obj.get("F")
                if tri is not None and obj.get("T") is None:
                    concat_tri.extend(vec_map(map, tri))
        shell_count = len(concat_tri)

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static:
                map = tag[name]
                tet = obj.get("T")
                tri = obj.get("F")
                if tet is not None and tri is not None:
                    concat_tri.extend(vec_map(map, tri))
                    concat_tet.extend(vec_map(map, tet))

        pbar.update(1)
        for name, obj in self._object.items():
            if not obj.static:
                map = tag[name]
                for p in obj._pin:
                    concat_pin.append(
                        PinData(
                            index=[map[vi] for vi in p.index],
                            keyframe=p.keyframe,
                            spin=p.spinner,
                            should_unpin=p.should_unpin,
                            pull_strength=p.pull_strength,
                            transition=p.transition,
                        )
                    )
                stitch_ind = obj.get("Ind")
                stitch_w = obj.get("W")
                if stitch_ind is not None and stitch_w is not None:
                    concat_stitch_ind.extend(vec_map(map, stitch_ind))
                    concat_stitch_w.extend(stitch_w)

        pbar.update(1)
        for name, obj in self._object.items():
            if obj.static:
                color = obj.get("color")
                offset = len(concat_static_vert)
                tri = obj.get("F")
                vert = obj.get("V")
                if tri is not None:
                    concat_static_tri.extend(tri + offset)
                if vert is not None:
                    concat_static_vert.extend(obj.apply_transform(vert))
                    concat_static_color.extend([color] * len(vert))

        self._save_func()
        pbar.update(1)

        fixed = FixedScene(
            self._plot,
            self.info.name,
            concat_vert,
            concat_color,
            concat_vel,
            concat_uv,
            np.array(concat_rod),
            np.array(concat_tri),
            np.array(concat_tet),
            self._wall,
            self._sphere,
            (rod_vert_start, rod_vert_end),
            (shell_vert_start, shell_vert_end),
            rod_count,
            shell_count,
        )

        if len(concat_pin):
            fixed.set_pin(concat_pin)

        if len(concat_static_vert):
            fixed.set_static(
                np.array(concat_static_vert),
                np.array(concat_static_tri),
                np.array(concat_static_color),
            )

        if len(concat_stitch_ind) and len(concat_stitch_w):
            fixed.set_stitch(
                np.array(concat_stitch_ind),
                np.array(concat_stitch_w),
            )

        return fixed


class Object:
    """The object class."""

    def __init__(self, asset: AssetManager, name: str):
        self._asset = asset
        self._name = name
        self._static = False
        self.clear()

    @property
    def name(self) -> str:
        """Get name of the object."""
        return self._name

    @property
    def static(self) -> bool:
        """Get whether the object is static."""
        return self._static

    def clear(self):
        """Clear the object data."""
        self._param = {}
        self._at = [0.0, 0.0, 0.0]
        self._scale = 1.0
        self._rotation = np.eye(3)
        self._color = []
        self._static_color = [0.75, 0.75, 0.75]
        self._default_color = [1.0, 0.85, 0.0]
        self._velocity = [0, 0, 0]
        self._pin: list[PinHolder] = []
        self._normalize = False
        self._stitch = None
        self._uv = None

    def report(self):
        """Report the object data."""
        print("at:", self._at)
        print("scale:", self._scale)
        print("rotation:")
        print(self._rotation)
        print("color:", self._color)
        print("velocity:", self._velocity)
        print("normalize:", self._normalize)
        self.update_static()
        if self.static:
            print("pin: static")
        else:
            print("pin:", sum([len(p.index) for p in self._pin]))

    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        """Compute the bounding box of the object.

        Returns:
            tuple[np.ndarray, np.ndarray]: The dimensions and center of the bounding box.
        """
        vert = self.get("V")
        if vert is None:
            raise Exception("vertex does not exist")
        else:
            transformed = self.apply_transform(vert)
            max_x, max_y, max_z = np.max(transformed, axis=0)
            min_x, min_y, min_z = np.min(transformed, axis=0)
            return (
                np.array(
                    [
                        max_x - min_x,
                        max_y - min_y,
                        max_z - min_z,
                    ]
                ),
                np.array(
                    [(max_x + min_x) / 2.0, (max_y + min_y) / 2.0, (max_z + min_z) / 2]
                ),
            )

    def normalize(self) -> "Object":
        """Normalize the object  so that it fits within a unit cube.

        Returns:
            Object: The normalized object.
        """
        if self._normalize:
            raise Exception("already normalized")
        else:
            self._bbox, self._center = self.bbox()
            self._normalize = True
            return self

    def get(self, key: str) -> Optional[np.ndarray]:
        """Get an associated value of the object with respect to the key.

        Args:
            key (str): The key of the value.
        Returns:
            Optional[np.ndarray]: The value associated with the key.
        """
        if key == "color":
            if self._color:
                return np.array(self._color)
            else:
                if self.static:
                    return np.array(self._static_color)
                else:
                    return np.array(self._default_color)
        elif key == "Ind":
            if self._stitch is not None:
                return self._stitch[0]
            else:
                return None
        elif key == "W":
            if self._stitch is not None:
                return self._stitch[1]
            else:
                return None
        else:
            result = self._asset.fetch.get(self._name)
            if key in result.keys():
                return result[key]
            else:
                return None

    def vertex(self) -> np.ndarray:
        """Get the transformed vertices of the object.

        Returns:
            np.ndarray: The transformed vertices.
        """
        vert = self.get("V")
        if vert is None:
            raise Exception("vertex does not exist")
        else:
            return self.apply_transform(vert)

    def grab(self, direction: list[float], eps: float = 1e-3) -> list[int]:
        """Grab vertices max towards a specified direction.

        Args:
            direction (list[float]): The direction vector.
            eps (float, optional): The distance threshold.

        Returns:
            list[int]: The indices of the grabbed vertices.
        """
        vert = self.vertex()
        val = np.max(np.dot(vert, np.array(direction)))
        return np.where(np.dot(vert, direction) > val - eps)[0].tolist()

    def set(self, key: str, value) -> "Object":
        """Set a parameter of the object.

        Args:
            key (str): The parameter key.
            value: The parameter value.

        Returns:
            Object: The object with the updated parameter.
        """
        self._param[key] = value
        return self

    def at(self, x: float, y: float, z: float) -> "Object":
        """Set the position of the object.

        Args:
            x (float): The x-coordinate.
            y (float): The y-coordinate.
            z (float): The z-coordinate.

        Returns:
            Object: The object with the updated position.
        """
        self._at = [x, y, z]
        return self

    def jitter(self, r: float = 1e-2) -> "Object":
        """Add random jitter to the position of the object.

        Args:
            r (float, optional): The jitter magnitude.

        Returns:
            Object: The object with the jittered position.
        """
        dx = np.random.random()
        dy = np.random.random()
        dz = np.random.random()
        self._at[0] += r * dx
        self._at[1] += r * dy
        self._at[2] += r * dz
        return self

    def atop(self, object: "Object", margin: float = 0.0) -> "Object":
        """Place the object on top of another object.

        Args:
            object (Object): The reference object.
            margin (float, optional): The margin between the objects. Defaults to 0.0.

        Returns:
            Object: The object placed on top of the reference object.
        """
        a_bbox, a_center = self.bbox()
        b_bbox, b_center = object.bbox()
        center = b_center - a_center
        center[1] += (a_bbox[1] + b_bbox[1]) / 2.0 + margin
        return self.at(*center)

    def scale(self, _scale: float) -> "Object":
        """Set the scale of the object.

        Args:
            _scale (float): The scale factor.

        Returns:
            Object: The object with the updated scale.
        """
        self._scale = _scale
        return self

    def rotate(self, angle: float, axis: str) -> "Object":
        """Rotate the object around a specified axis.

        Args:
            angle (float): The rotation angle in degrees.
            axis (str): The rotation axis ('x', 'y', or 'z').

        Returns:
            Object: The object with the updated rotation.
        """
        theta = angle / 180.0 * np.pi
        if axis.lower() == "x":
            self._rotation = np.array(
                [
                    [1, 0, 0],
                    [0, np.cos(theta), -np.sin(theta)],
                    [0, np.sin(theta), np.cos(theta)],
                ]
                @ self._rotation
            )
        elif axis.lower() == "y":
            self._rotation = np.array(
                [
                    [np.cos(theta), 0, np.sin(theta)],
                    [0, 1, 0],
                    [-np.sin(theta), 0, np.cos(theta)],
                ]
                @ self._rotation
            )
        elif axis.lower() == "z":
            self._rotation = np.array(
                [
                    [np.cos(theta), -np.sin(theta), 0],
                    [np.sin(theta), np.cos(theta), 0],
                    [0, 0, 1],
                ]
                @ self._rotation
            )
        else:
            raise Exception("invalid axis")
        return self

    def max(self, dim: int):
        """Get the maximum coordinate value along a specified dimension.

        Args:
            dim (int): The dimension index (0 for x, 1 for y, 2 for z).

        Returns:
            float: The maximum coordinate value.
        """
        vert = self.vertex()
        return np.max([x[dim] for x in vert])

    def min(self, dim: int):
        """Get the minimum coordinate value along a specified dimension.

        Args:
            dim (int): The dimension index (0 for x, 1 for y, 2 for z).

        Returns:
            float: The minimum coordinate value.
        """
        vert = self.vertex()
        return np.min([x[dim] for x in vert])

    def apply_transform(self, x: np.ndarray) -> np.ndarray:
        """Apply the object's transformation to a set of vertices.

        Args:
            x (np.ndarray): The vertices to transform.

        Returns:
            np.ndarray: The transformed vertices.
        """
        if len(x.shape) == 1:
            raise Exception("vertex should be 2D array")
        else:
            x = x.transpose()
        if self._normalize:
            x = (x - self._center) / np.max(self._bbox)
        x = self._rotation @ x
        x = x * self._scale + np.array(self._at).reshape((3, 1))
        return x.transpose()

    def static_color(self, red: float, green: float, blue: float) -> "Object":
        """Set the static color of the object.

        Args:
            red (float): The red component.
            green (float): The green component.
            blue (float): The blue component.

        Returns:
            Object: The object with the updated static color.
        """
        self._static_color = [red, green, blue]
        return self

    def default_color(self, red: float, green: float, blue: float) -> "Object":
        """Set the default color of the object.

        Args:
            red (float): The red component.
            green (float): The green component.
            blue (float): The blue component.

        Returns:
            Object: The object with the updated default color.
        """
        self._default_color = [red, green, blue]
        return self

    def color(self, red: float, green: float, blue: float) -> "Object":
        """Set the color of the object.

        Args:
            red (float): The red component.
            green (float): The green component.
            blue (float): The blue component.

        Returns:
            Object: The object with the updated color.
        """
        self._color = [red, green, blue]
        return self

    def velocity(self, u: float, v: float, w: float) -> "Object":
        """Set the velocity of the object.
        If the object is static, an exception is raised.

        Args:
            u (float): The velocity in the x-direction.
            v (float): The velocity in the y-direction.
            w (float): The velocity in the z-direction.

        Returns:
            Object: The object with the updated velocity.
        """
        if self.static:
            raise Exception("object is static")
        else:
            self._velocity = np.array([u, v, w])
            return self

    def update_static(self):
        """Check if the object is static.
        When all the vertices are pinned and the object is not moving,
        it is considered static.

        Returns:
            bool: True if the object is static, False otherwise.
        """
        if not self._pin:
            self._static = False
            return

        for p in self._pin:
            if len(p.keyframe) > 0 or p.pull_strength:
                return False
            if len(p.spinner) > 0:
                return False

        vert = self.get("V")
        if vert is None:
            self._static = False
            return

        vert_flag = np.zeros(len(vert))
        for p in self._pin:
            for i in p.index:
                vert_flag[i] = 1
        self._static = np.sum(vert_flag) == len(vert)

    def pin(self, ind: Optional[list[int]] = None) -> PinHolder:
        """Set specified vertices as pinned.

        Args:
            ind (Optional[list[int]], optional): The indices of the vertices to pin.
            If None, all vertices are pinned. Defaults to None.

        Returns:
            PinHolder: The pin holder.
        """
        if ind is None:
            vert: np.ndarray = self.vertex()
            ind = list(range(len(vert)))
        for p in self._pin:
            if set(p.index) & set(ind):
                raise Exception("duplicated indices")

        holder = PinHolder(self, ind)
        self._pin.append(holder)
        return holder

    def pull_pin(
        self, strength: float = 1.0, ind: Optional[list[int]] = None
    ) -> PinHolder:
        """Pin and pull the object at specified vertices.

        Args:
            strength (float, optional): The pull strength. Defaults to 1.0.
            ind (Optional[list[int]], optional): The indices of the vertices to pin. Defaults to None.

        Returns:
            PinHolder: The pinholder with the pinned and pulled vertices.
        """
        holder = self.pin(ind)
        holder.set_pull(strength)
        return holder

    def stitch(self, name: str) -> "Object":
        """Apply stitch to the object.

        Args:
            name (str): The name of stitch registered in the asset manager.

        Returns:
            Object: The stitched object.
        """
        if self.static:
            raise Exception("object is static")
        else:
            stitch = self._asset.fetch.get(name)
            if "Ind" not in stitch.keys():
                raise Exception("Ind not found in stitch")
            elif "W" not in stitch.keys():
                raise Exception("W not found in stitch")
            else:
                self._stitch = (stitch["Ind"], stitch["W"])
                return self

    def direction(self, _ex: list[float], _ey: list[float]) -> "Object":
        """Set two orthogonal directions of a shell required for Baraff-Witkin model.

        Args:
            _ex (list[float]): The 3D x-direction vector.
            _ey (list[float]): The 3D y-direction vector.

        Returns:
            Object: The object with the updated direction.
        """
        vert, tri = self.vertex(), self.get("F")
        ex = np.array(_ex)
        ex = ex / np.linalg.norm(ex)
        ey = np.array(_ey)
        ey = ey / np.linalg.norm(ey)
        if abs(np.dot(ex, ey)) > EPS:
            raise Exception(f"ex and ey must be orthogonal. ex: {ex}, ey: {ey}")
        elif vert is None:
            raise Exception("vertex does not exist")
        elif tri is None:
            raise Exception("face does not exist")
        else:
            for t in tri:
                a, b, c = vert[t]
                n = np.cross(b - a, c - a)
                n = n / np.linalg.norm(n)
                if abs(np.dot(n, _ex)) > EPS:
                    raise Exception(
                        f"ex must be orthogonal to the face normal. normal: {n}"
                    )
                elif abs(np.dot(n, _ey)) > EPS:
                    raise Exception(
                        f"ey must be orthogonal to the face normal. normal: {n}"
                    )
            self._uv = np.zeros((len(vert), 2))
            for i, x in enumerate(vert):
                u, v = x.dot(ex), x.dot(ey)
                self._uv[i] = [u, v]
        return self
