# =============================================================================
# Minet Mediacloud CLI Action
# =============================================================================
#
# Logic of the `mc` action.
#
from minet.cli.utils import die


def mediacloud_action(cli_args):

    # A token is needed to be able to access the API
    if not cli_args.token:
        die(
            [
                "A token is needed to be able to access Mediacloud's API.",
                "You can provide one using the `--token` argument.",
            ]
        )

    if cli_args.mc_action == "medias":
        from minet.cli.mediacloud.medias import mediacloud_medias_action

        mediacloud_medias_action(cli_args)

    if cli_args.mc_action == "topic":
        from minet.cli.mediacloud.topic import mediacloud_topic_action

        mediacloud_topic_action(cli_args)

    elif cli_args.mc_action == "search":
        from minet.cli.mediacloud.search import mediacloud_search_action

        mediacloud_search_action(cli_args)
