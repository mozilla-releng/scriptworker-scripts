# Manually edit UPPER_CASE words

node 'YOUR_LOANER.dev.releng.use1.mozilla.com' {
    # the pins must come *before* the toplevel include
    $aspects = [ 'low-security' ]
    $slave_trustlevel = 'try'
    $pin_puppet_server = 'releng-puppet2.srv.releng.scl3.mozilla.com'
    $pin_puppet_env = 'YOUR_PUPPET_ENV'
    $pushapk_scriptworker_env = 'dev'
    $timezone = 'UTC'
    include toplevel::server::pushapkscriptworker
}
