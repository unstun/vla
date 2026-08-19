#!/usr/bin/perl
# portable_timeout.pl SECONDS COMMAND [ARGS...]
#
# macOS ships no GNU coreutils `timeout`, which implement.md assumes for every
# model process. This shim reproduces the needed behaviour: run COMMAND in its
# own process group, send SIGTERM to the whole group after SECONDS, SIGKILL
# five seconds later, and exit 124 on timeout (GNU convention).
use strict;
use warnings;
use POSIX qw(:errno_h);

my $timeout = shift @ARGV;
die "usage: portable_timeout.pl SECONDS COMMAND [ARGS...]\n"
    unless defined $timeout && $timeout =~ /^\d+$/ && @ARGV;

my $pid = fork();
die "portable_timeout: fork failed: $!\n" unless defined $pid;
if ($pid == 0) {
    setpgrp(0, 0);
    exec { $ARGV[0] } @ARGV;
    die "portable_timeout: exec failed: $!\n";
}

my $timed_out = 0;
$SIG{ALRM} = sub {
    $timed_out = 1;
    kill 'TERM', -$pid;
    select(undef, undef, undef, 5.0);
    kill 'KILL', -$pid;
};
alarm($timeout);

my $status;
while (1) {
    my $reaped = waitpid($pid, 0);
    $status = $?;
    last if $reaped == $pid;
    next if $reaped == -1 && $! == EINTR;
    last;
}
alarm(0);

if ($timed_out) {
    print STDERR "portable_timeout: TIMEOUT after ${timeout}s: @ARGV\n";
    exit 124;
}
exit(($status & 127) ? 128 + ($status & 127) : ($status >> 8));
