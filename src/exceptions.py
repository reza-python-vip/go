"""Custom exceptions for testers."""


class NodeTestError(Exception):
    """Base exception for node testing errors."""

    pass


class XrayConfigError(NodeTestError):
    """Error in Xray configuration."""

    pass


class XrayStartupError(NodeTestError):
    """Error starting Xray process."""

    pass


class ConnectionTestError(NodeTestError):
    """Error testing connection through node."""

    pass
