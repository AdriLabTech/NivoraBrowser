/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

const { AddonManager } = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");

const ADDON_ID = "unsigned@nivora.test";
const SIGNATURES_PREF = "xpinstall.signatures.required";

function makeUnsignedXPI() {
  const file = Services.dirsvc.get("TmpD", Ci.nsIFile);
  file.append("nivora-unsigned.xpi");
  file.createUnique(Ci.nsIFile.NORMAL_FILE_TYPE, 0o644);

  const zip = Cc["@mozilla.org/zipwriter;1"].createInstance(Ci.nsIZipWriter);
  zip.open(file, 0x04 | 0x08 | 0x20);
  const stream = Cc["@mozilla.org/io/string-input-stream;1"].createInstance(Ci.nsIStringInputStream);
  stream.setUTF8Data(
    JSON.stringify({
      manifest_version: 2,
      name: "Nivora unsigned test",
      version: "1.0",
      browser_specific_settings: { gecko: { id: ADDON_ID } },
    })
  );
  zip.addEntryStream("manifest.json", 0, Ci.nsIZipWriter.COMPRESSION_NONE, stream, false);
  zip.close();
  registerCleanupFunction(() => file.remove(false));
  return file;
}

add_task(async function test_the_shipped_default_refuses_an_unsigned_extension() {
  await SpecialPowers.pushPrefEnv({ clear: [[SIGNATURES_PREF]] });
  ok(Services.prefs.getBoolPref(SIGNATURES_PREF), "signatures are required once the test harness override is cleared");

  const install = await AddonManager.getInstallForFile(makeUnsignedXPI());
  is(install.error, AddonManager.ERROR_SIGNEDSTATE_REQUIRED, "the install is refused because it is unsigned");
  is(await AddonManager.getAddonByID(ADDON_ID), null, "the extension is not installed");

  await SpecialPowers.popPrefEnv();
});

add_task(async function test_control_the_same_file_installs_when_the_requirement_is_off() {
  await SpecialPowers.pushPrefEnv({ set: [[SIGNATURES_PREF, false]] });

  const install = await AddonManager.getInstallForFile(makeUnsignedXPI());
  isnot(install.error, AddonManager.ERROR_SIGNEDSTATE_REQUIRED, "nothing refuses it for lack of a signature");
  ok(install.state !== AddonManager.STATE_DOWNLOAD_FAILED, "the file is a valid extension");
  install.cancel?.();

  await SpecialPowers.popPrefEnv();
});
