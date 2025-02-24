from Box2D import b2Contact, b2ContactListener

from ..utils.const import GOAL_COLLISIONS_REQUIRED


class CollisionListener(b2ContactListener):
    """
    Custom collision listener that records continuous collisions between target bodies.
    """

    def __init__(self, required_collisions: int = GOAL_COLLISIONS_REQUIRED) -> None:
        super().__init__()
        self.goal_reached = False
        self.current_frame = 0
        self.required_collisions = required_collisions
        self.is_colliding = False
        self.collision_count = 0

    def BeginContact(self, contact: b2Contact) -> None:
        """Record when target bodies start colliding."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = True

    def EndContact(self, contact: b2Contact) -> None:
        """Record when target bodies stop colliding."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = False

    def update(self) -> None:
        """
        Update collision counter and check if continuous collision count
        meets the threshold.
        """
        self.current_frame += 1
        if self.is_colliding:
            self.collision_count += 1
            if self.collision_count >= self.required_collisions:
                self.goal_reached = True
        else:
            self.collision_count = 0
