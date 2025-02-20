from Box2D import b2Contact, b2ContactListener

from src.utils.const import COLLISION_DURATION_THRESHOLD


class CollisionListener(b2ContactListener):
    """
    Custom collision listener that records collisions between two specific body indices.
    We identify the colliding bodies by matching fixture.userData or body.userData.
    Tracks collision duration to ensure it meets the threshold requirement.
    """

    def __init__(self) -> None:
        super().__init__()
        self.goal_reached = False
        self.collision_start_frame = None
        self.current_frame = 0
        self.is_colliding = False

    def BeginContact(self, contact: b2Contact) -> None:
        """Start tracking collision duration when target bodies collide."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = True
                if self.collision_start_frame is None:
                    self.collision_start_frame = self.current_frame

    def EndContact(self, contact: b2Contact) -> None:
        """Reset collision tracking when target bodies separate."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = False
                self.collision_start_frame = None

    def update(self) -> None:
        """Update frame counter and check if collision duration meets threshold."""
        self.current_frame += 1

        if self.is_colliding and self.collision_start_frame is not None:
            collision_duration = self.current_frame - self.collision_start_frame
            if collision_duration >= COLLISION_DURATION_THRESHOLD:
                self.goal_reached = True
