/* Any copyright is dedicated to the Public Domain.
   https://creativecommons.org/publicdomain/zero/1.0/ */

"use strict";

// The Foundation acceptance steps F-02 to F-05 and F-08 (docs/TESTING.md section 3.1), run in the built
// browser: HTTPS identity, tabs, history, forms, video, a PDF, and the pages of the browser itself. Pages are
// data: URLs, so the test needs no server of its own.

const page = text =>
  "data:text/html," + encodeURIComponent(`<!doctype html><title>${text}</title><body><h1>${text}</h1></body>`);

ChromeUtils.defineESModuleGetters(this, {
  TabStateFlusher: "moz-src:///browser/components/sessionstore/TabStateFlusher.sys.mjs",
});

// Closed tabs are only remembered for pages with a real address, so the tab test uses the test server's.
const served = i => `https://example.com/?nivora-tab=${i}`;

const FORM =
  "data:text/html," +
  encodeURIComponent(`<!doctype html><title>form</title><form id="f">
    <input id="name"><textarea id="note"></textarea>
    <select id="choice"><option value="a">a</option><option value="b">b</option></select>
    <input id="agree" type="checkbox"></form>`);

const WEBM = "data:video/webm;base64,GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKHgQJChYECGFOAZwEAAAAAAANvEU2bdLpNu4tTq4QVSalmU6yBoU27i1OrhBZUrmtTrIHYTbuMU6uEElTDZ1OsggEeTbuMU6uEHFO7a1OsggNZ7AEAAAAAAABZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVSalmsirXsYMPQkBNgI1MYXZmNjAuMTYuMTAwV0GNTGF2ZjYwLjE2LjEwMESJiECPQAAAAAAAFlSua8GuAQAAAAAAADjXgQFzxYjBepO6wvCQPpyBACK1nIN1bmSIgQCGhVZfVlA4g4EBI+ODhAP5QKrgibCBoLqBeJqBAhJUw2f8c3OgY8CAZ8iaRaOHRU5DT0RFUkSHjUxhdmY2MC4xNi4xMDBzc9ZjwItjxYjBepO6wvCQPmfIoUWjh0VOQ09ERVJEh5RMYXZjNjAuMzEuMTAyIGxpYnZweGfIoUWjiERVUkFUSU9ORIeTMDA6MDA6MDEuMDAwMDAwMDAwAB9DtnVBtOeBAKPDgQAAgFAGAJ0BKqAAeAAARwiFhYiFhIgCAgAGIhJu3LXnDSa5zhpNc5w0muc4aTXOcNJrnOGk1znDSa5zhpNcMP5oAKOYgQBDABECAAEQEAAYABhYL/QACICBDLAAo5iBAIUAEQIAARAQABgAGFgv9AAIgIEMsACjmIEAyAARAgABEBAAGAAYWC/0AAiAgQywAKOYgQELABECAAEQEAAYABhYL/QACICBDLAAo5iBAU0AEQIAARAQABgAGFgv9AAIgIEMsACjmIEBkAARAgABEBAAGAAYWC/0AAiAgQywAKOYgQHTABECAAEQEBRgAGFgv9AAIgIEMsAAo5iBAhUAEQIAARAQABgAGFgv9AAIgIEMsACjmIECWAARAgABEBAAGAAYWC/0AAiAgQywAKOYgQKbABECAAEQEAAYABhYL/QACICBDLAAo5iBAt0AEQIAARAQABgAGFgv9AAIgIEMsACjmIEDIAARAgABEBAAGAAYWC/0AAiAgQywAKOYgQNjABECAAEQEAAYABhYL/QACICBDLAAo5iBA6UAEQIAARAQABgAGFgv9AAIgIEMsAAcU7trkbuPs4EAt4r3gQHxggGf8IED";
const PDF = "data:application/pdf;base64,JVBERi0xLjQKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFI+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlL1BhZ2VzL0tpZHNbMyAwIFJdL0NvdW50IDE+PgplbmRvYmoKMyAwIG9iago8PC9UeXBlL1BhZ2UvUGFyZW50IDIgMCBSL01lZGlhQm94WzAgMCAyMDAgMjAwXS9Db250ZW50cyA0IDAgUi9SZXNvdXJjZXM8PC9Gb250PDwvRjEgNSAwIFI+Pj4+Pj4KZW5kb2JqCjQgMCBvYmoKPDwvTGVuZ3RoIDM3Pj4Kc3RyZWFtCkJUIC9GMSAyNCBUZiAyMCAxMDAgVGQgKE5pdm9yYSkgVGogRVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjw8L1R5cGUvRm9udC9TdWJ0eXBlL1R5cGUxL0Jhc2VGb250L0hlbHZldGljYT4+CmVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1NCAwMDAwMCBuIAowMDAwMDAwMTA1IDAwMDAwIG4gCjAwMDAwMDAyMTcgMDAwMDAgbiAKMDAwMDAwMDMwMiAwMDAwMCBuIAp0cmFpbGVyCjw8L1NpemUgNi9Sb290IDEgMCBSPj4Kc3RhcnR4cmVmCjM2NQolJUVPRgo=";

add_task(async function test_F02_an_https_page_is_shown_as_secure() {
  await BrowserTestUtils.withNewTab("https://example.com/", async () => {
    await TestUtils.waitForCondition(() => gIdentityHandler._isSecureConnection, "the connection is reported as secure");
    Assert.ok(gBrowser.currentURI.spec.startsWith("https://example.com"), "and it is the page that was asked for");
  });
});

add_task(async function test_F03_five_tabs_close_three_reopen_one() {
  const before = gBrowser.tabs.length;
  const tabs = [];
  for (let i = 0; i < 5; i++) {
    tabs.push(await BrowserTestUtils.openNewForegroundTab(gBrowser, served(i)));
  }
  Assert.equal(gBrowser.tabs.length, before + 5, "five tabs are open");
  for (const tab of tabs.slice(0, 3)) {
    // The session store learns a tab's state in batches; flush it so that closing remembers the tab.
    await TabStateFlusher.flush(tab.linkedBrowser);
    await BrowserTestUtils.removeTab(tab);
  }
  Assert.equal(gBrowser.tabs.length, before + 2, "three were closed");
  const restored = SessionStore.undoCloseTab(window, 0);
  await TestUtils.waitForCondition(() => gBrowser.tabs.length === before + 3, "one tab is back");
  const lastEntry = tab => JSON.parse(SessionStore.getTabState(tab)).entries.at(-1).url;
  Assert.equal(lastEntry(restored), served(2), "and it is the one closed last");
  for (const tab of [restored, ...tabs.slice(3)]) {
    BrowserTestUtils.removeTab(tab);
  }
});

add_task(async function test_F04_back_and_forward_follow_the_history() {
  await BrowserTestUtils.withNewTab(page("first"), async browser => {
    const at = url => TestUtils.waitForCondition(() => browser.currentURI.spec === url, `at ${url.slice(-30)}`);
    BrowserTestUtils.startLoadingURIString(browser, page("second"));
    await at(page("second"));
    await TestUtils.waitForCondition(() => browser.canGoBack, "there is somewhere to go back to");
    browser.goBack();
    await at(page("first"));
    await TestUtils.waitForCondition(() => browser.canGoForward, "and forward");
    browser.goForward();
    await at(page("second"));
    Assert.equal(browser.currentURI.spec, page("second"), "history was respected both ways");
  });
});

add_task(async function test_F05_a_form_takes_typing_a_video_plays_and_a_pdf_renders() {
  await BrowserTestUtils.withNewTab(FORM, async browser => {
    await SpecialPowers.spawn(browser, [], () => content.document.getElementById("name").focus());
    await EventUtils.sendString("Nivora", window);
    const state = await SpecialPowers.spawn(browser, [], () => {
      const doc = content.document;
      doc.getElementById("note").value = "two words";
      doc.getElementById("choice").value = "b";
      doc.getElementById("agree").checked = true;
      return {
        name: doc.getElementById("name").value,
        note: doc.getElementById("note").value,
        choice: doc.getElementById("choice").value,
        agree: doc.getElementById("agree").checked,
      };
    });
    Assert.deepEqual(state, { name: "Nivora", note: "two words", choice: "b", agree: true }, "typed values are kept");
  });

  await BrowserTestUtils.withNewTab(page("video"), async browser => {
    const info = await SpecialPowers.spawn(browser, [WEBM], async src => {
      const video = content.document.createElement("video");
      video.muted = true;
      content.document.body.append(video);
      video.src = src;
      await new Promise((resolve, reject) => {
        video.onloadeddata = resolve;
        video.onerror = () => reject(new Error("video error " + (video.error && video.error.code)));
      });
      await video.play().catch(() => {});
      await new Promise(resolve => content.setTimeout(resolve, 400));
      return { width: video.videoWidth, height: video.videoHeight, time: video.currentTime, ready: video.readyState };
    });
    Assert.deepEqual([info.width, info.height], [160, 120], "the video was decoded at its size");
    Assert.greater(info.time, 0, "and it plays");
  });

  await BrowserTestUtils.withNewTab(PDF, async browser => {
    const pages = await SpecialPowers.spawn(browser, [], async () => {
      const viewer = () => content.wrappedJSObject.PDFViewerApplication;
      await ContentTaskUtils.waitForCondition(() => viewer()?.pagesCount, "the PDF viewer has the document");
      return viewer().pagesCount;
    });
    Assert.equal(pages, 1, "the PDF opens in the built-in viewer");
  });
});

add_task(async function test_F08_the_browsers_own_pages_open_and_a_private_window_opens() {
  for (const url of ["about:preferences", "about:addons", "about:downloads", "about:policies", "about:support"]) {
    await BrowserTestUtils.withNewTab(url, async browser => {
      const state = await SpecialPowers.spawn(browser, [], async () => {
        await ContentTaskUtils.waitForCondition(() => content.document.readyState === "complete", "loaded");
        return { uri: content.document.documentURI, title: content.document.title };
      });
      Assert.ok(!state.uri.startsWith("about:neterror"), `${url} opens (${state.uri})`);
    });
  }
  const win = await BrowserTestUtils.openNewBrowserWindow({ private: true });
  Assert.ok(PrivateBrowsingUtils.isWindowPrivate(win), "a private window opens");
  await BrowserTestUtils.closeWindow(win);
});
